#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"; CONFIG="default"; SPLIT="validation"
OFFSET=25; N=25; EXPECTED_TOTAL=3381
UA="ProjectBrain-HLE-QueryPlannerV2-ConsumedDiag/1.0"
SCHEMA="PROJECT_BRAIN_HLE_QUERY_PLANNER_V2_CONSUMED_DIAGNOSTIC_V1"

def canon_obj(x:Any)->bytes:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha_obj(x:Any)->str:return hashlib.sha256(canon_obj(x)).hexdigest()

def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    url="https://datasets-server.huggingface.co/rows?"+q
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r: obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL: raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N: raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j; row=item.get("row") or {}
                if int(item.get("row_idx",-1))!=idx: raise RuntimeError("ORDER_MISMATCH")
                qv=row.get("question"); av=row.get("answer")
                if not isinstance(qv,str) or not qv.strip() or not isinstance(av,str) or not av.strip(): raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":qv,"answer":av})
            return out
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","rows":N,
         "slice":"ROWS_25_TO_49_ALREADY_CONSUMED_QUERY_PLANNER_V2_DIAGNOSTIC",
         "questions_manifest_sha256":sha_obj(qs),"questions":qs,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_open_web_fallback_v1 import retrieve
    out=retrieve(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,
                 max_views=5,limit_per_view=8,timeout=10)
    records=[]
    for row in out.get("candidates") or []:
        records.append({
            "backend":str(row.get("discovery_backend") or "UNKNOWN"),
            "title":str(row.get("title") or ""),
            "snippet":str(row.get("snippet") or ""),
            "url":str(row.get("url") or ""),
            "query":str(row.get("query") or ""),
            "query_rank":int(row.get("query_rank") or 0),
        })
    return {
        "row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
        "status":out.get("status"),"records":records,"record_count":len(records),
        "backend_health":out.get("backend_health") or {},
        "views":out.get("views") or [],
        "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0,
    }

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text()); qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=N or sha_obj(qs)!=qdoc.get("questions_manifest_sha256"): raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fs={pool.submit(trace_one,x):x for x in qs}
        for f,x in fs.items():
            try: out.append(f.result())
            except Exception as e:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "status":"TRACE_EXCEPTION:"+type(e).__name__,"records":[],"record_count":0,
                            "backend_health":{},"views":[],"gold_accessed":False,"external_model_calls":0,
                            "external_reasoning_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    doc={"schema":SCHEMA,"phase":"RETRIEVAL_TRACE_SEALED_BEFORE_GOLD","trace_count":len(out),
         "questions_manifest_sha256":qdoc["questions_manifest_sha256"],"trace_manifest_sha256":sha_obj(out),
         "traces":out,"gold_loaded_by_trace_process":False,"external_model_calls_total":0,
         "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":doc["phase"],"trace_manifest_sha256":doc["trace_manifest_sha256"],
                      "record_count":sum(x["record_count"] for x in out)},sort_keys=True))

def norm(v:str)->str:
    x=unicodedata.normalize("NFKD",str(v or "")).casefold()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(x.split())

def contains(text:str,gold:str)->bool:
    t=norm(text); g=norm(gold)
    if not t or not g:return False
    if g in t:return True
    ga=re.sub(r"^(?:a|an|the)\s+","",g).strip()
    return bool(ga) and len(ga)>=4 and ga in t

def score(tpath:Path,spath:Path)->None:
    td=json.loads(tpath.read_text()); traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=N or sha_obj(traces)!=td.get("trace_manifest_sha256"): raise RuntimeError("TRACE_INVALID")
    rows=fetch_rows(); gold={r["row_idx"]:r["answer"] for r in rows}
    any_n=0; backend_hits=defaultdict(int); backend_health=defaultdict(lambda:defaultdict(int)); per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]; hit=False; bhit=set()
        for rec in tr.get("records") or []:
            h=contains(str(rec.get("title") or ""),g) or contains(str(rec.get("snippet") or ""),g)
            if h:
                hit=True; bhit.add(str(rec.get("backend") or "UNKNOWN"))
        any_n+=int(hit)
        for b in bhit: backend_hits[b]+=1
        for b,hrow in (tr.get("backend_health") or {}).items():
            backend_health[b][str(hrow.get("health") or "UNKNOWN")]+=1
        per.append({"row_idx":tr["row_idx"],"retrieval_any_hit":hit,"backend_hits":sorted(bhit),
                    "record_count":tr.get("record_count",0),"status":tr.get("status")})
    summary={
        "schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"sample_size":N,
        "slice":"ROWS_25_TO_49_ALREADY_CONSUMED_QUERY_PLANNER_V2_DIAGNOSTIC",
        "baseline_full_retrieval_any_hit_rate":0.52,
        "baseline_discovery_surface_hit_rate":0.44,
        "retrieval_any_hit":any_n,"retrieval_any_hit_rate":any_n/N,
        "absolute_delta_vs_discovery_baseline":any_n/N-0.44,
        "absolute_delta_vs_full_retrieval_reference":any_n/N-0.52,
        "backend_hit_counts":dict(sorted(backend_hits.items())),
        "backend_health_sample_counts":{k:dict(sorted(v.items())) for k,v in sorted(backend_health.items())},
        "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
        "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,"per_slot":per
    }
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--trace",type=Path,required=True); a.add_argument("--workers",type=int,default=4)
    a=sub.add_parser("score"); a.add_argument("--trace",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare": prepare(x.questions)
    elif x.cmd=="trace": trace(x.questions,x.trace,x.workers)
    else: score(x.trace,x.summary)
if __name__=="__main__": main()
