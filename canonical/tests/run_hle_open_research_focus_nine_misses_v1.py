#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json
from pathlib import Path
from canonical.tests import run_hle_wikipedia_via_bing_nine_misses_v1 as base

SCHEMA="PROJECT_BRAIN_HLE_OPEN_RESEARCH_FOCUS_NINE_MISSES_V1"

def prepare(path:Path):
    base.prepare(path)

def trace_one(item):
    from canonical.runtime.bound_capabilities.open_web_source_candidate_discovery import discover
    try:
        out=discover(item["question"],limit=12,timeout=10)
        candidates=list(out.get("candidates") or [])
        provenance=list(out.get("retrieval_provenance") or [])
        errors=list(out.get("backend_errors") or [])
        focus=dict(out.get("query_focus") or {})
        status=str(out.get("status") or "UNKNOWN")
    except Exception as exc:
        candidates=[]; provenance=[]; errors=[{"backend":"TOPLEVEL","error_class":type(exc).__name__}]
        focus={}; status="FAILED:"+type(exc).__name__
    return {
      "row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
      "status":status,
      "query_focus":{
        "status":focus.get("status"),"query":focus.get("query"),"query_sha256":focus.get("query_sha256"),
        "method":focus.get("method")
      },
      "records":[{
        "url":str(x.get("url") or ""),"title":str(x.get("title") or ""),
        "snippet":str(x.get("snippet") or ""),"backend":str(x.get("discovery_backend") or "")
      } for x in candidates],
      "retrieval_provenance":provenance,"backend_errors":errors,
      "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0,
    }

def trace(qpath:Path,tpath:Path,workers:int):
    qdoc=json.loads(qpath.read_text()); qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(base.TARGET_IDS) or base.sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),3))) as pool:
        futs={pool.submit(trace_one,x):x for x in qs}
        for f,x in futs.items():
            try: out.append(f.result())
            except Exception as exc:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "status":"TRACE_EXCEPTION:"+type(exc).__name__,"query_focus":{},"records":[],
                            "retrieval_provenance":[],"backend_errors":[],"gold_accessed":False,
                            "external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    doc={"schema":SCHEMA,"phase":"OPEN_RESEARCH_TRACES_SEALED_BEFORE_GOLD","target_ids":base.TARGET_IDS,
         "questions_manifest_sha256":qdoc["questions_manifest_sha256"],"trace_manifest_sha256":base.sha_obj(out),
         "traces":out,"gold_loaded_by_trace_process":False,"external_model_calls_total":0,
         "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":doc["phase"],"trace_manifest_sha256":doc["trace_manifest_sha256"],
                      "candidate_count":sum(len(x["records"]) for x in out)},sort_keys=True))

def score(tpath:Path,spath:Path):
    td=json.loads(tpath.read_text()); traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(base.TARGET_IDS) or base.sha_obj(traces)!=td.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_INVALID")
    gold={r["row_idx"]:r["answer"] for r in base.fetch_rows()}
    hit_ids=[]; backend_hits={}; focus_queries={}; per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]; hit=False; hit_backends=set()
        for x in tr.get("records") or []:
            h=base.contains(str(x.get("title") or ""),g) or base.contains(str(x.get("snippet") or ""),g)
            if h:
                hit=True
                hit_backends.add(str(x.get("backend") or "UNKNOWN"))
        if hit: hit_ids.append(tr["row_idx"])
        for b in hit_backends: backend_hits[b]=backend_hits.get(b,0)+1
        focus_queries[str(tr["row_idx"])]=(tr.get("query_focus") or {}).get("query")
        per.append({"row_idx":tr["row_idx"],"hit":hit,"hit_backends":sorted(hit_backends),
                    "candidate_count":len(tr.get("records") or [])})
    summary={"schema":SCHEMA,"target_ids":base.TARGET_IDS,"sample_size":len(base.TARGET_IDS),
             "hit_ids":hit_ids,"hit_count":len(hit_ids),"hit_rate":len(hit_ids)/len(base.TARGET_IDS),
             "remaining_miss_ids":[i for i in base.TARGET_IDS if i not in hit_ids],
             "backend_hit_counts":backend_hits,"focus_queries":focus_queries,"per_slot":per,
             "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("OPEN_RESEARCH_FOCUS_RESULT",json.dumps({k:v for k,v in summary.items() if k not in {"per_slot","focus_queries"}},sort_keys=True))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--trace",type=Path,required=True); a.add_argument("--workers",type=int,default=2)
    a=sub.add_parser("score"); a.add_argument("--trace",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare": prepare(x.questions)
    elif x.cmd=="trace": trace(x.questions,x.trace,x.workers)
    else: score(x.trace,x.summary)
if __name__=="__main__": main()
