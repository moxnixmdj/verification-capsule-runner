#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"
CONFIG="default"; SPLIT="validation"; OFFSET=25; N=25; EXPECTED_TOTAL=3381
TARGET_IDS=[27,32,37,38,39,41,43,44,45]
SCHEMA="PROJECT_BRAIN_HLE_WIKIPEDIA_VIA_BING_PAIRED_NINE_MISSES_V1"
UA="ProjectBrain-HLE-WikipediaViaBing/1.0"

def canon_obj(x:Any)->bytes:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha_obj(x:Any)->str:
    return hashlib.sha256(canon_obj(x)).hexdigest()

def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    url="https://datasets-server.huggingface.co/rows?"+q
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r:
                obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL: raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N: raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j
                if idx not in TARGET_IDS: continue
                if int(item.get("row_idx",-1))!=idx: raise RuntimeError("ORDER_MISMATCH")
                row=item.get("row") or {}
                question=row.get("question"); answer=row.get("answer")
                if not isinstance(question,str) or not question.strip() or not isinstance(answer,str) or not answer.strip(): raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":question,"answer":answer})
            if [x["row_idx"] for x in out]!=TARGET_IDS: raise RuntimeError("TARGET_IDS_MISMATCH")
            return out
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","target_ids":TARGET_IDS,
         "questions_manifest_sha256":sha_obj(qs),"questions":qs,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime import hle_native_retrieval_query_planner_v1 as planner
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search
    plan=planner.plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7)
    rows={"general":[],"wiki_site":[]}; receipts={"general":[],"wiki_site":[]}
    for vi,v in enumerate(plan.get("views") or [],1):
        q=" ".join(str(v.get("query") or "").split())
        for label,query in (("general",q),("wiki_site","site:en.wikipedia.org "+q)):
            try:
                rr=list(rich_search(query,limit=8))
                status="PASS"
            except Exception as exc:
                rr=[]; status="FAILED:"+type(exc).__name__
            receipts[label].append({"view":vi,"method":v.get("method"),"query_sha256":hashlib.sha256(query.encode()).hexdigest(),
                                    "status":status,"result_count":len(rr)})
            for x in rr:
                rows[label].append({"view":vi,"title":str(x.get("title") or ""),"snippet":str(x.get("snippet") or ""),
                                    "url":str(x.get("url") or ""),"rank":int(x.get("rank") or 99)})
    return {"row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
            "records":rows,"receipts":receipts,"gold_accessed":False,"external_model_calls":0,
            "external_reasoning_model_calls":0,"model_dependency_count":0}

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text()); qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(TARGET_IDS) or sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),3))) as pool:
        futs={pool.submit(trace_one,x):x for x in qs}
        for f,x in futs.items():
            try: out.append(f.result())
            except Exception as exc:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "records":{"general":[],"wiki_site":[]},"receipts":{"general":[],"wiki_site":[]},
                            "trace_exception":type(exc).__name__,"gold_accessed":False,"external_model_calls":0,
                            "external_reasoning_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    doc={"schema":SCHEMA,"phase":"PAIRED_TRACES_SEALED_BEFORE_GOLD","target_ids":TARGET_IDS,
         "questions_manifest_sha256":qdoc["questions_manifest_sha256"],"trace_manifest_sha256":sha_obj(out),
         "traces":out,"gold_loaded_by_trace_process":False,"external_model_calls_total":0,
         "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":doc["phase"],"trace_manifest_sha256":doc["trace_manifest_sha256"]},sort_keys=True))

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
    if not isinstance(traces,list) or len(traces)!=len(TARGET_IDS) or sha_obj(traces)!=td.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_INVALID")
    gold={r["row_idx"]:r["answer"] for r in fetch_rows()}
    counts={"general":0,"wiki_site":0}; site_unique=[]; general_unique=[]; union=[]; per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]; hits={}
        for label in ("general","wiki_site"):
            hit=any(contains(str(x.get("title") or ""),g) or contains(str(x.get("snippet") or ""),g)
                    for x in (tr.get("records") or {}).get(label,[]))
            hits[label]=hit; counts[label]+=int(hit)
        if hits["wiki_site"] and not hits["general"]: site_unique.append(tr["row_idx"])
        if hits["general"] and not hits["wiki_site"]: general_unique.append(tr["row_idx"])
        if hits["general"] or hits["wiki_site"]: union.append(tr["row_idx"])
        per.append({"row_idx":tr["row_idx"],"general_hit":hits["general"],"wiki_site_hit":hits["wiki_site"]})
    summary={"schema":SCHEMA,"target_ids":TARGET_IDS,"sample_size":len(TARGET_IDS),
             "general_hits":counts["general"],"wiki_site_hits":counts["wiki_site"],
             "wiki_site_unique_hit_ids":site_unique,"wiki_site_unique_hit_count":len(site_unique),
             "general_unique_hit_ids":general_unique,"union_hit_ids":union,"union_hit_count":len(union),
             "remaining_miss_ids":[i for i in TARGET_IDS if i not in union],"per_slot":per,
             "external_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("WIKI_SITE_RESULT",json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

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
