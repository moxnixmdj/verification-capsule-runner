#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"; CONFIG="default"; SPLIT="validation"
OFFSET=25; N=25; TARGET_IDS=[32,37,38,41,43,45]; EXPECTED_TOTAL=3381
UA="ProjectBrain-HLE-RelationWikiComposition/1.0"
SCHEMA="PROJECT_BRAIN_HLE_RELATION_WIKIPEDIA_COMPOSITION_PAIRED_CONSUMED_V1"

def canon_obj(x:Any)->bytes:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha_obj(x:Any)->str:return hashlib.sha256(canon_obj(x)).hexdigest()
def norm(v:str)->str:
    x=unicodedata.normalize("NFKD",str(v or "")).lower()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    x=re.sub(r"\b(?:a|an|the)\b"," ",x)
    return " ".join(x.split())

def fetch_rows():
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    url="https://datasets-server.huggingface.co/rows?"+q
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r: obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N:raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j
                if int(item.get("row_idx",-1))!=idx:raise RuntimeError("ORDER_MISMATCH")
                row=item.get("row") or {};qv=row.get("question");a=row.get("answer")
                if not isinstance(qv,str) or not qv.strip() or not isinstance(a,str) or not a.strip():raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":qv,"answer":a})
            return out
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)

def prepare(path:Path):
    rows=[r for r in fetch_rows() if r["row_idx"] in TARGET_IDS]
    if [r["row_idx"] for r in rows]!=TARGET_IDS:raise RuntimeError("TARGET_ORDER_MISMATCH")
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","dataset":DATASET,"split":SPLIT,
         "slice":"SIX_ALREADY_CONSUMED_RESIDUALS_AFTER_TRANSPORT_AND_RELATION_GAINS",
         "target_ids":TARGET_IDS,"questions_manifest_sha256":sha_obj(qs),"questions":qs,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def plan_one(item):
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    from canonical.runtime.hle_relation_requirement_compiler_v1 import compile_requirements
    base=plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7)
    rel=compile_requirements(task_id=item["task_id"],question=item["question"],max_queries=8)
    b=[{"query":x["query"],"method":x.get("method"),"source":"BASELINE"} for x in base["views"]]
    seen={x["query"].casefold() for x in b};a=list(b);added=[]
    for x in rel.get("requirements") or []:
        q=str(x.get("query") or "").strip()
        if not q or q.casefold() in seen:continue
        seen.add(q.casefold())
        rec={"query":q,"method":x.get("method"),"relation_type":x.get("relation_type"),"source":"RELATION_ADDITIVE"}
        a.append(rec);added.append(rec)
    return {"row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
            "baseline":b,"augmented":a,"relation_added":added}

def retrieve_query(q):
    from canonical.runtime.hle_wikipedia_bing_transport_v1 import retrieve
    out=retrieve(query=q,limit=3,timeout=20.0)
    if out.get("gold_accessed") is not False or int(out.get("external_model_calls",0) or 0)!=0 or int(out.get("model_dependency_count",0) or 0)!=0:
        raise RuntimeError("AUTHORITY_ACCOUNTING_FAILURE")
    return {"query":q,"status":out.get("status"),"pages":out.get("pages") or [],
            "search_attempts":out.get("search_attempts") or []}

def trace(qpath:Path,tpath:Path,workers:int):
    doc=json.loads(qpath.read_text());qs=doc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(TARGET_IDS) or sha_obj(qs)!=doc.get("questions_manifest_sha256"):raise RuntimeError("QUESTIONS_INVALID")
    plans=[plan_one(x) for x in qs]
    unique=[];seen=set()
    for p in plans:
        for x in p["augmented"]:
            k=x["query"].casefold()
            if k not in seen:seen.add(k);unique.append(x["query"])
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),3))) as pool:
        futs={pool.submit(retrieve_query,q):q for q in unique}
        for f,q in futs.items():
            try:results[q.casefold()]=f.result()
            except Exception as e:results[q.casefold()]={"query":q,"status":"FAILED_RETRYABLE:"+type(e).__name__,"pages":[],"search_attempts":[]}
    traces=[]
    for p in plans:
        def collect(spec):
            return [{**x,**results[x["query"].casefold()]} for x in spec]
        traces.append({"row_idx":p["row_idx"],"task_id":p["task_id"],"question_sha256":p["question_sha256"],
                       "baseline":collect(p["baseline"]),"augmented":collect(p["augmented"]),
                       "relation_added":p["relation_added"],"gold_accessed":False,
                       "external_model_calls":0,"model_dependency_count":0})
    sealed={"schema":SCHEMA,"phase":"PAIRED_RELATION_WIKI_TRACES_SEALED_BEFORE_GOLD","target_ids":TARGET_IDS,
            "questions_manifest_sha256":doc["questions_manifest_sha256"],"trace_manifest_sha256":sha_obj(traces),
            "unique_query_count":len(unique),"traces":traces,"gold_loaded_by_trace_process":False,
            "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(sealed,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":sealed["phase"],"trace_manifest_sha256":sealed["trace_manifest_sha256"],
                      "unique_queries":len(unique),"relation_queries":sum(len(p["relation_added"]) for p in plans)},sort_keys=True))

def surface(rows):
    vals=[]
    for qr in rows:
        for p in qr.get("pages") or []:
            if p.get("status")=="PASS":
                vals.extend([str(p.get("url") or ""),str(p.get("text") or "")])
    return " ".join(vals)

def score(tpath:Path,spath:Path):
    sealed=json.loads(tpath.read_text());traces=sealed.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(TARGET_IDS) or sha_obj(traces)!=sealed.get("trace_manifest_sha256"):raise RuntimeError("TRACE_INVALID")
    rows={r["row_idx"]:r for r in fetch_rows() if r["row_idx"] in TARGET_IDS}
    bh=[];ah=[];per=[]
    for tr in traces:
        idx=tr["row_idx"];ng=norm(rows[idx]["answer"])
        b=bool(ng) and ng in norm(surface(tr["baseline"]))
        a=bool(ng) and ng in norm(surface(tr["augmented"]))
        if b:bh.append(idx)
        if a:ah.append(idx)
        per.append({"row_idx":idx,"baseline_hit":b,"augmented_hit":a,"composition_unique_gain":a and not b,
                    "relation_methods":[x.get("method") for x in tr.get("relation_added") or []]})
    unique=[x for x in ah if x not in bh];lost=[x for x in bh if x not in ah]
    summary={"schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"sample_size":len(TARGET_IDS),"target_ids":TARGET_IDS,
             "baseline_hit_ids":bh,"baseline_hits":len(bh),"augmented_hit_ids":ah,"augmented_hits":len(ah),
             "composition_unique_gain_ids":unique,"composition_unique_gain_count":len(unique),
             "baseline_unique_loss_ids":lost,"causal_pass":len(unique)>0 and not lost,"per_slot":per,
             "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,
             "hard_nonclaim":"CONSUMED_PUBLIC_COMPOSITION_GAIN_IS_NOT_HLE_SCORE_OR_TERMINAL_CAPABILITY_CREDIT"}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("RELATION_WIKI_COMPOSITION",json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare");a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace");a.add_argument("--questions",type=Path,required=True);a.add_argument("--trace",type=Path,required=True);a.add_argument("--workers",type=int,default=2)
    a=sub.add_parser("score");a.add_argument("--trace",type=Path,required=True);a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":prepare(x.questions)
    elif x.cmd=="trace":trace(x.questions,x.trace,x.workers)
    else:score(x.trace,x.summary)
if __name__=="__main__":main()
