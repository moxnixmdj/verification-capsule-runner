#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
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
BASELINE_HIT_COUNT=15
BASELINE_SAMPLE_SIZE=25
BASELINE_RUN_ID=38145869751
MISS_ROWS=(27,32,36,37,38,39,41,43,44,45)
UA="ProjectBrain-HLE-DiverseFallback-PriorMisses/1.0"
SCHEMA="PROJECT_BRAIN_HLE_DIVERSE_FALLBACK_PRIOR_MISSES_V1"

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
            out=[]
            wanted=set(MISS_ROWS)
            for item in rows:
                idx=int(item.get("row_idx",-1))
                if idx not in wanted:
                    continue
                row=item.get("row") or {}
                qv=row.get("question"); av=row.get("answer")
                if not isinstance(qv,str) or not qv.strip():
                    raise RuntimeError("QUESTION_INVALID")
                if not isinstance(av,str) or not av.strip():
                    raise RuntimeError("ANSWER_INVALID")
                out.append({"row_idx":idx,"question":qv,"answer":av})
            out.sort(key=lambda x:x["row_idx"])
            if [x["row_idx"] for x in out]!=list(MISS_ROWS):
                raise RuntimeError("MISS_ROW_SET_MISMATCH")
            return out
        except Exception:
            if attempt==3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[
        {
            "row_idx":r["row_idx"],
            "task_id":f"triviaqa_validation_row_{r['row_idx']}",
            "question":r["question"],
            "question_sha256":hashlib.sha256(r["question"].encode()).hexdigest(),
        }
        for r in rows
    ]
    doc={
        "schema":SCHEMA,
        "phase":"QUESTIONS_ONLY_PREPARED",
        "selection_reason":"TEN_PRIOR_MISSES_FROM_SEALED_SHORT_SEED_BASELINE",
        "baseline_run_id":BASELINE_RUN_ID,
        "baseline_hit_count":BASELINE_HIT_COUNT,
        "baseline_sample_size":BASELINE_SAMPLE_SIZE,
        "row_indices":list(MISS_ROWS),
        "questions_manifest_sha256":sha_obj(qs),
        "questions":qs,
        "gold_written":False,
        "hle_questions_consumed":0,
    }
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_open_web_fallback_v1 import retrieve

    out=retrieve(
        task_id=item["task_id"],
        question=item["question"],
        has_nonempty_image_payload=False,
        max_views=7,
        limit_per_view=9,
        timeout=15,
    )
    records=[]
    for row in out.get("candidates") or []:
        records.append({
            "backend":str(row.get("discovery_backend") or "UNKNOWN"),
            "title":str(row.get("title") or ""),
            "snippet":str(row.get("snippet") or ""),
            "url":str(row.get("url") or ""),
            "query_rank":row.get("query_rank"),
            "query_method":row.get("query_method"),
        })
    return {
        "row_idx":item["row_idx"],
        "task_id":item["task_id"],
        "question_sha256":item["question_sha256"],
        "fallback_status":out.get("status"),
        "records":records,
        "record_count":len(records),
        "backend_health":out.get("backend_health") or {},
        "blocked_candidate_count":int(out.get("blocked_candidate_count") or 0),
        "failed_retryable_view_count":int(out.get("failed_retryable_view_count") or 0),
        "gold_accessed":bool(out.get("gold_accessed")),
        "external_model_calls":int(out.get("external_model_calls") or 0),
        "external_reasoning_model_calls":int(out.get("external_reasoning_model_calls") or 0),
        "model_dependency_count":int(out.get("model_dependency_count") or 0),
        "answer_authority":bool(out.get("answer_authority")),
        "correctness_authority":bool(out.get("correctness_authority")),
    }

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text())
    qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(MISS_ROWS):
        raise RuntimeError("QUESTIONS_INVALID")
    if sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_MANIFEST_MISMATCH")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),4))) as pool:
        fs={pool.submit(trace_one,x):x for x in qs}
        for f,x in fs.items():
            try:
                out.append(f.result())
            except Exception as e:
                out.append({
                    "row_idx":x["row_idx"],
                    "task_id":x["task_id"],
                    "question_sha256":x["question_sha256"],
                    "fallback_status":"TRACE_EXCEPTION:"+type(e).__name__,
                    "records":[],
                    "record_count":0,
                    "backend_health":{},
                    "blocked_candidate_count":0,
                    "failed_retryable_view_count":7,
                    "gold_accessed":False,
                    "external_model_calls":0,
                    "external_reasoning_model_calls":0,
                    "model_dependency_count":0,
                    "answer_authority":False,
                    "correctness_authority":False,
                })
    out.sort(key=lambda x:x["row_idx"])
    for x in out:
        if x["gold_accessed"]:
            raise RuntimeError("GOLD_ACCESSED_DURING_TRACE")
        if x["external_model_calls"] or x["external_reasoning_model_calls"] or x["model_dependency_count"]:
            raise RuntimeError("EXTERNAL_COGNITION_DURING_TRACE")
        if x["answer_authority"] or x["correctness_authority"]:
            raise RuntimeError("AUTHORITY_LEAK_DURING_TRACE")
    doc={
        "schema":SCHEMA,
        "phase":"DIVERSE_FALLBACK_TRACE_SEALED_BEFORE_GOLD",
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
        "trace_count":len(out),
        "record_count":sum(x["record_count"] for x in out),
        "blocked_candidate_count":sum(x["blocked_candidate_count"] for x in out),
    },sort_keys=True))

def norm(v:str)->str:
    x=unicodedata.normalize("NFKD",str(v or "")).casefold()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(x.split())

def contains(text:str,gold:str)->bool:
    t=norm(text); g=norm(gold)
    if not t or not g:
        return False
    if g in t:
        return True
    ga=re.sub(r"^(?:a|an|the)\s+","",g).strip()
    return bool(ga) and len(ga)>=4 and ga in t

def score(tpath:Path,spath:Path)->None:
    td=json.loads(tpath.read_text())
    traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(MISS_ROWS):
        raise RuntimeError("TRACE_INVALID")
    if sha_obj(traces)!=td.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_MANIFEST_MISMATCH")
    rows=fetch_rows()
    gold={r["row_idx"]:r["answer"] for r in rows}
    per=[]
    recovered=[]
    diversified_recovered=[]
    backend_hit_counts=Counter()
    backend_health_counts=Counter()
    for tr in traces:
        g=gold[tr["row_idx"]]
        hits=[]
        for rec in tr.get("records") or []:
            backend=str(rec.get("backend") or "UNKNOWN")
            hit=contains(str(rec.get("title") or ""),g) or contains(str(rec.get("snippet") or ""),g)
            if hit:
                hits.append(backend)
                backend_hit_counts[backend]+=1
        any_hit=bool(hits)
        if any_hit:
            recovered.append(tr["row_idx"])
        if any(x in {"DUCKDUCKGO_HTML","CROSSREF"} for x in hits):
            diversified_recovered.append(tr["row_idx"])
        for backend,stats in (tr.get("backend_health") or {}).items():
            backend_health_counts[f"{backend}:{stats.get('health')}"]+=1
        per.append({
            "row_idx":tr["row_idx"],
            "gold":g,
            "fallback_hit":any_hit,
            "hit_backends":sorted(set(hits)),
            "record_count":tr.get("record_count",0),
            "fallback_status":tr.get("fallback_status"),
            "blocked_candidate_count":tr.get("blocked_candidate_count",0),
        })
    k=len(recovered)
    union_hits=BASELINE_HIT_COUNT+k
    summary={
        "schema":SCHEMA,
        "phase":"SCORED_AFTER_TRACE_SEAL",
        "dataset":DATASET,
        "split":SPLIT,
        "baseline_run_id":BASELINE_RUN_ID,
        "baseline_hit_count":BASELINE_HIT_COUNT,
        "baseline_retrieval_any_hit_rate":BASELINE_HIT_COUNT/BASELINE_SAMPLE_SIZE,
        "prior_miss_count":len(MISS_ROWS),
        "fallback_recovered_prior_misses":k,
        "fallback_recovery_rate_on_prior_misses":k/len(MISS_ROWS),
        "recovered_row_indices":recovered,
        "diversified_backend_recovered_row_indices":diversified_recovered,
        "diversified_backend_recovered_count":len(diversified_recovered),
        "combined_union_hit_count":union_hits,
        "combined_union_retrieval_any_hit_rate":union_hits/BASELINE_SAMPLE_SIZE,
        "absolute_recall_gain":k/BASELINE_SAMPLE_SIZE,
        "backend_hit_counts":dict(sorted(backend_hit_counts.items())),
        "backend_health_counts":dict(sorted(backend_health_counts.items())),
        "external_model_calls_total":0,
        "external_reasoning_model_calls_total":0,
        "model_dependency_count_total":0,
        "hle_questions_consumed":0,
        "hle_gold_consumed":0,
        "hle_score_credit":0,
        "per_slot":per,
    }
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))
    for row in per:
        print(json.dumps(row,ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare")
    a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace")
    a.add_argument("--questions",type=Path,required=True)
    a.add_argument("--trace",type=Path,required=True)
    a.add_argument("--workers",type=int,default=2)
    a=sub.add_parser("score")
    a.add_argument("--trace",type=Path,required=True)
    a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":
        prepare(x.questions)
    elif x.cmd=="trace":
        trace(x.questions,x.trace,x.workers)
    else:
        score(x.trace,x.summary)

if __name__=="__main__":
    main()
