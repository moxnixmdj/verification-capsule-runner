#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"
CONFIG="default"
SPLIT="validation"
OFFSET=25
N=25
EXPECTED_TOTAL=3381
TARGET_IDS=[27,32,37,38,39,41,43,44,45]
UA="ProjectBrain-HLE-WikipediaBing-ConsumedDiagnostic/1.0"
SCHEMA="PROJECT_BRAIN_HLE_WIKIPEDIA_BING_CONSUMED_DIAGNOSTIC_V1"

def canon_obj(x:Any)->bytes:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()

def sha_obj(x:Any)->str:
    return hashlib.sha256(canon_obj(x)).hexdigest()

def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    url="https://datasets-server.huggingface.co/rows?"+q
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r:
                obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:
                raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N:
                raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j
                if int(item.get("row_idx",-1))!=idx:
                    raise RuntimeError("ORDER_MISMATCH")
                row=item.get("row") or {}
                question=row.get("question");answer=row.get("answer")
                if not isinstance(question,str) or not question.strip() or not isinstance(answer,str) or not answer.strip():
                    raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":question,"answer":answer})
            return out
        except Exception as e:
            last=e
            if attempt==3:raise
            time.sleep(2**attempt)
    raise RuntimeError(type(last).__name__ if last else "FETCH_FAILED")

def prepare(path:Path)->None:
    rows=[r for r in fetch_rows() if r["row_idx"] in TARGET_IDS]
    if [r["row_idx"] for r in rows]!=TARGET_IDS:
        raise RuntimeError("TARGET_ORDER_MISMATCH")
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","dataset":DATASET,"split":SPLIT,
         "slice":"ALREADY_CONSUMED_SHARED_MISSES_9","target_ids":TARGET_IDS,
         "questions_manifest_sha256":sha_obj(qs),"questions":qs,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    from canonical.runtime.hle_wikipedia_bing_transport_v1 import retrieve
    plan=plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7)
    views=[]
    pages=[]
    for vrank,v in enumerate(plan["views"]):
        out=retrieve(query=v["query"],limit=3,timeout=20.0)
        if out.get("gold_accessed") is not False or int(out.get("external_model_calls",0) or 0)!=0 or int(out.get("model_dependency_count",0) or 0)!=0:
            raise RuntimeError("AUTHORITY_ACCOUNTING_FAILURE")
        views.append({
          "rank":vrank,"method":v.get("method"),"query":v["query"],"query_sha256":v["query_sha256"],
          "status":out.get("status"),"candidate_url_count":out.get("candidate_url_count",0),
          "successful_page_count":out.get("successful_page_count",0),
          "failed_retryable_page_count":out.get("failed_retryable_page_count",0),
          "search_attempts":out.get("search_attempts") or [],
        })
        for p in out.get("pages") or []:
            if p.get("status")=="PASS":
                pages.append({"url":p.get("url"),"text":p.get("text"),"query_rank":vrank,"page_rank":p.get("rank")})
    dedup=[];seen=set()
    for p in pages:
        u=str(p.get("url") or "")
        if not u or u in seen:continue
        seen.add(u);dedup.append(p)
    return {
      "row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
      "views":views,"pages":dedup,"page_count":len(dedup),
      "trace_payload_sha256":sha_obj({"views":views,"pages":dedup}),
      "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0,
    }

def trace(qpath:Path,tpath:Path,workers:int)->None:
    doc=json.loads(qpath.read_text())
    qs=doc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(TARGET_IDS) or sha_obj(qs)!=doc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),4))) as pool:
        futs={pool.submit(trace_one,x):x for x in qs}
        for f,x in futs.items():
            try:out.append(f.result())
            except Exception as e:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "views":[],"pages":[],"page_count":0,"trace_error":type(e).__name__+":"+str(e)[:300],
                            "trace_payload_sha256":sha_obj([]),"gold_accessed":False,"external_model_calls":0,
                            "external_reasoning_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    sealed={"schema":SCHEMA,"phase":"RETRIEVAL_TRACE_SEALED_BEFORE_GOLD","target_ids":TARGET_IDS,
            "questions_manifest_sha256":doc["questions_manifest_sha256"],"trace_manifest_sha256":sha_obj(out),
            "traces":out,"gold_loaded_by_trace_process":False,"external_model_calls_total":0,
            "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(sealed,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":sealed["phase"],"trace_manifest_sha256":sealed["trace_manifest_sha256"],
                      "pages":sum(x["page_count"] for x in out),"trace_errors":sum("trace_error" in x for x in out)},sort_keys=True))

_ARTICLE=re.compile(r"\b(a|an|the)\b",re.I)
def norm(v:str)->str:
    x=unicodedata.normalize("NFKD",str(v or "")).lower()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(_ARTICLE.sub(" ",x).split())

def score(tpath:Path,spath:Path)->None:
    sealed=json.loads(tpath.read_text())
    traces=sealed.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(TARGET_IDS) or sha_obj(traces)!=sealed.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_INVALID")
    rows={r["row_idx"]:r for r in fetch_rows() if r["row_idx"] in TARGET_IDS}
    hits=[];per=[];engine_counts={};status_counts={}
    for tr in traces:
        idx=tr["row_idx"];gold=rows[idx]["answer"];ng=norm(gold)
        surface=" ".join([str(p.get("url") or "")+" "+str(p.get("text") or "") for p in tr.get("pages") or []])
        hit=bool(ng) and ng in norm(surface)
        if hit:hits.append(idx)
        for v in tr.get("views") or []:
            status=str(v.get("status") or "UNKNOWN");status_counts[status]=status_counts.get(status,0)+1
            for a in v.get("search_attempts") or []:
                eng=str(a.get("engine") or "UNKNOWN")
                engine_counts[eng]=engine_counts.get(eng,0)+1
        per.append({"row_idx":idx,"hit":hit,"page_count":tr.get("page_count",0),"trace_error":tr.get("trace_error")})
    summary={
      "schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"slice":"ALREADY_CONSUMED_SHARED_MISSES_9",
      "sample_size":len(TARGET_IDS),"target_ids":TARGET_IDS,"hit_ids":hits,"hit_count":len(hits),
      "retrieval_any_hit_rate":len(hits)/len(TARGET_IDS),"unique_gain_over_v1_v2_shared_miss_baseline":len(hits),
      "remaining_miss_ids":[x for x in TARGET_IDS if x not in hits],
      "transport_status_counts":status_counts,"search_engine_attempt_counts":engine_counts,"per_slot":per,
      "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
      "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,
      "causal_pass":len(hits)>0,
      "hard_nonclaim":"CONSUMED_PUBLIC_RETRIEVAL_GAIN_IS_NOT_HLE_SCORE_OR_TERMINAL_CAPABILITY_CREDIT"
    }
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare");a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace");a.add_argument("--questions",type=Path,required=True);a.add_argument("--trace",type=Path,required=True);a.add_argument("--workers",type=int,default=3)
    a=sub.add_parser("score");a.add_argument("--trace",type=Path,required=True);a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":prepare(x.questions)
    elif x.cmd=="trace":trace(x.questions,x.trace,x.workers)
    else:score(x.trace,x.summary)

if __name__=="__main__":main()
