#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"
CONFIG="default"
SPLIT="validation"
BASE_OFFSET=25
BASE_N=25
EXPECTED_TOTAL=3381
BASELINE_RUN_ID=38145869751
BASELINE_HIT_COUNT=15
BASELINE_SAMPLE_SIZE=25
MISS_ROWS=(27,32,36,37,38,39,41,43,44,45)
MAX_FETCHES_PER_ROW=6
UA="ProjectBrain-HLE-MaterializePriorMisses/1.0"
SCHEMA="PROJECT_BRAIN_HLE_MATERIALIZE_PRIOR_MISSES_V1"
TAG=re.compile(r"<[^>]+>")

def canon_obj(x:Any)->bytes:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()

def sha_obj(x:Any)->str:
    return hashlib.sha256(canon_obj(x)).hexdigest()

def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({
        "dataset":DATASET,"config":CONFIG,"split":SPLIT,
        "offset":BASE_OFFSET,"length":BASE_N,
    })
    url="https://datasets-server.huggingface.co/rows?"+q
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r:
                obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:
                raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=BASE_N:
                raise RuntimeError("ROW_COUNT_MISMATCH")
            wanted=set(MISS_ROWS); out=[]
            for item in rows:
                idx=int(item.get("row_idx",-1))
                if idx not in wanted: continue
                row=item.get("row") or {}
                qv=row.get("question"); av=row.get("answer")
                if not isinstance(qv,str) or not qv.strip(): raise RuntimeError("QUESTION_INVALID")
                if not isinstance(av,str) or not av.strip(): raise RuntimeError("ANSWER_INVALID")
                out.append({"row_idx":idx,"question":qv,"answer":av})
            out.sort(key=lambda x:x["row_idx"])
            if [x["row_idx"] for x in out]!=list(MISS_ROWS):
                raise RuntimeError("MISS_ROW_SET_MISMATCH")
            return out
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[{
        "row_idx":r["row_idx"],
        "task_id":f"triviaqa_validation_row_{r['row_idx']}",
        "question":r["question"],
        "question_sha256":hashlib.sha256(r["question"].encode()).hexdigest(),
    } for r in rows]
    doc={
        "schema":SCHEMA,
        "phase":"QUESTIONS_ONLY_PREPARED",
        "selection_reason":"TEN_PRIOR_MISSES_FROM_SEALED_60_PERCENT_BASELINE",
        "baseline_run_id":BASELINE_RUN_ID,
        "row_indices":list(MISS_ROWS),
        "questions_manifest_sha256":sha_obj(qs),
        "questions":qs,
        "gold_written":False,
        "hle_questions_consumed":0,
    }
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def select_fetch_candidates(candidates:list[dict[str,Any]])->list[dict[str,Any]]:
    # Minimum-information materialization: at most one candidate from each query
    # view, preserving the answer-blind fallback order.
    out=[]; seen_urls=set(); seen_views=set()
    for row in candidates:
        if not isinstance(row,dict): continue
        url=str(row.get("url") or "").strip()
        view=row.get("query_rank")
        if not url or url in seen_urls or view in seen_views: continue
        seen_urls.add(url); seen_views.add(view)
        out.append(row)
        if len(out)>=MAX_FETCHES_PER_ROW: break
    return out

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_open_web_fallback_v1 import retrieve
    from canonical.runtime.root2_hle_opus55_tool_adapter_v1 import fetch_web

    search=retrieve(
        task_id=item["task_id"],
        question=item["question"],
        has_nonempty_image_payload=False,
        max_views=7,
        limit_per_view=9,
        timeout=15,
    )
    candidates=list(search.get("candidates") or [])
    selected=select_fetch_candidates(candidates)
    materialized=[]
    for row in selected:
        url=str(row.get("url") or "")
        rec={
            "url":url,
            "search_backend":str(row.get("discovery_backend") or "UNKNOWN"),
            "query_rank":row.get("query_rank"),
            "query_method":row.get("query_method"),
            "search_title":str(row.get("title") or ""),
            "search_snippet":str(row.get("snippet") or ""),
        }
        try:
            f=fetch_web(url,timeout=15,max_bytes=500000)
            rec.update({
                "fetch_status":str(f.get("status") or ""),
                "final_url":str(f.get("final_url") or ""),
                "http_status":int(f.get("http_status") or 0),
                "body_sha256":str(f.get("body_sha256") or ""),
                "body_excerpt":str(f.get("body_excerpt") or ""),
                "fetch_retryable":False,
            })
        except Exception as exc:
            rec.update({
                "fetch_status":"FAILED:"+type(exc).__name__,
                "final_url":"",
                "http_status":0,
                "body_sha256":"",
                "body_excerpt":"",
                "fetch_retryable":True,
                "error":str(exc)[:500],
            })
        materialized.append(rec)
    return {
        "row_idx":item["row_idx"],
        "task_id":item["task_id"],
        "question_sha256":item["question_sha256"],
        "search_status":search.get("status"),
        "search_candidate_count":len(candidates),
        "selected_fetch_count":len(selected),
        "materialized":materialized,
        "backend_health":search.get("backend_health") or {},
        "blocked_candidate_count":int(search.get("blocked_candidate_count") or 0),
        "gold_accessed":bool(search.get("gold_accessed")),
        "external_model_calls":int(search.get("external_model_calls") or 0),
        "external_reasoning_model_calls":int(search.get("external_reasoning_model_calls") or 0),
        "model_dependency_count":int(search.get("model_dependency_count") or 0),
        "answer_authority":bool(search.get("answer_authority")),
        "correctness_authority":bool(search.get("correctness_authority")),
    }

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text())
    qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(MISS_ROWS):
        raise RuntimeError("QUESTIONS_INVALID")
    if sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_MANIFEST_MISMATCH")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),3))) as pool:
        futures={pool.submit(trace_one,x):x for x in qs}
        for f,x in futures.items():
            try:
                out.append(f.result())
            except Exception as exc:
                out.append({
                    "row_idx":x["row_idx"],"task_id":x["task_id"],
                    "question_sha256":x["question_sha256"],
                    "search_status":"TRACE_EXCEPTION:"+type(exc).__name__,
                    "search_candidate_count":0,"selected_fetch_count":0,"materialized":[],
                    "backend_health":{},"blocked_candidate_count":0,
                    "gold_accessed":False,"external_model_calls":0,
                    "external_reasoning_model_calls":0,"model_dependency_count":0,
                    "answer_authority":False,"correctness_authority":False,
                })
    out.sort(key=lambda x:x["row_idx"])
    for x in out:
        if x["gold_accessed"]: raise RuntimeError("GOLD_ACCESSED_DURING_TRACE")
        if x["external_model_calls"] or x["external_reasoning_model_calls"] or x["model_dependency_count"]:
            raise RuntimeError("EXTERNAL_COGNITION_DURING_TRACE")
        if x["answer_authority"] or x["correctness_authority"]:
            raise RuntimeError("AUTHORITY_LEAK_DURING_TRACE")
    doc={
        "schema":SCHEMA,
        "phase":"SEARCH_AND_PAGE_MATERIALIZATION_SEALED_BEFORE_GOLD",
        "baseline_run_id":BASELINE_RUN_ID,
        "trace_count":len(out),
        "questions_manifest_sha256":qdoc["questions_manifest_sha256"],
        "trace_manifest_sha256":sha_obj(out),
        "traces":out,
        "gold_loaded_by_trace_process":False,
        "external_model_calls_total":0,
        "external_reasoning_model_calls_total":0,
        "model_dependency_count_total":0,
        "hle_questions_consumed":0,
        "hle_gold_consumed":0,
    }
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "phase":doc["phase"],
        "trace_manifest_sha256":doc["trace_manifest_sha256"],
        "selected_fetch_count":sum(x["selected_fetch_count"] for x in out),
        "successful_fetch_count":sum(
            1 for x in out for r in x["materialized"]
            if str(r.get("fetch_status") or "")=="PASS"
        ),
    },sort_keys=True))

def norm(v:str)->str:
    x=html.unescape(TAG.sub(" ",str(v or "")))
    x=unicodedata.normalize("NFKD",x).casefold()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(x.split())

def contains(text:str,gold:str)->bool:
    t=norm(text); g=norm(gold)
    if not t or not g: return False
    if g in t: return True
    ga=re.sub(r"^(?:a|an|the)\s+","",g).strip()
    return bool(ga) and len(ga)>=4 and ga in t

def score(tpath:Path,spath:Path)->None:
    td=json.loads(tpath.read_text()); traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(MISS_ROWS):
        raise RuntimeError("TRACE_INVALID")
    if sha_obj(traces)!=td.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_MANIFEST_MISMATCH")
    gold={r["row_idx"]:r["answer"] for r in fetch_rows()}
    search_recovered=[]; body_recovered=[]; body_only_recovered=[]
    fetch_status=Counter(); backend_body_hits=Counter(); per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]
        search_hit=False; body_hit=False; body_hit_backends=[]
        for rec in tr.get("materialized") or []:
            sh=contains(str(rec.get("search_title") or ""),g) or contains(str(rec.get("search_snippet") or ""),g)
            bh=contains(str(rec.get("body_excerpt") or ""),g)
            search_hit=search_hit or sh
            body_hit=body_hit or bh
            fetch_status[str(rec.get("fetch_status") or "UNKNOWN")]+=1
            if bh:
                b=str(rec.get("search_backend") or "UNKNOWN")
                backend_body_hits[b]+=1
                body_hit_backends.append(b)
        if search_hit: search_recovered.append(tr["row_idx"])
        if body_hit: body_recovered.append(tr["row_idx"])
        if body_hit and not search_hit: body_only_recovered.append(tr["row_idx"])
        per.append({
            "row_idx":tr["row_idx"],"gold":g,
            "search_surface_hit_this_epoch":search_hit,
            "materialized_body_hit":body_hit,
            "materialized_body_only_hit":body_hit and not search_hit,
            "body_hit_backends":sorted(set(body_hit_backends)),
            "selected_fetch_count":tr.get("selected_fetch_count",0),
            "search_candidate_count":tr.get("search_candidate_count",0),
        })
    union_rows=sorted(set(search_recovered)|set(body_recovered))
    k=len(union_rows)
    summary={
        "schema":SCHEMA,"phase":"SCORED_AFTER_MATERIALIZATION_SEAL",
        "dataset":DATASET,"split":SPLIT,
        "baseline_run_id":BASELINE_RUN_ID,
        "baseline_hit_count":BASELINE_HIT_COUNT,
        "baseline_retrieval_any_hit_rate":BASELINE_HIT_COUNT/BASELINE_SAMPLE_SIZE,
        "prior_miss_count":len(MISS_ROWS),
        "search_surface_recovered_rows":search_recovered,
        "search_surface_recovered_count":len(search_recovered),
        "materialized_body_recovered_rows":body_recovered,
        "materialized_body_recovered_count":len(body_recovered),
        "materialized_body_only_recovered_rows":body_only_recovered,
        "materialized_body_only_recovered_count":len(body_only_recovered),
        "new_union_recovered_rows":union_rows,
        "new_union_recovered_count":k,
        "combined_union_hit_count":BASELINE_HIT_COUNT+k,
        "combined_union_retrieval_any_hit_rate":(BASELINE_HIT_COUNT+k)/BASELINE_SAMPLE_SIZE,
        "absolute_recall_gain":k/BASELINE_SAMPLE_SIZE,
        "fetch_status_counts":dict(sorted(fetch_status.items())),
        "backend_body_hit_counts":dict(sorted(backend_body_hits.items())),
        "external_model_calls_total":0,
        "external_reasoning_model_calls_total":0,
        "model_dependency_count_total":0,
        "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,
        "per_slot":per,
    }
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))
    for row in per: print(json.dumps(row,ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--trace",type=Path,required=True); a.add_argument("--workers",type=int,default=2)
    a=sub.add_parser("score"); a.add_argument("--trace",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare": prepare(x.questions)
    elif x.cmd=="trace": trace(x.questions,x.trace,x.workers)
    else: score(x.trace,x.summary)

if __name__=="__main__":
    main()
