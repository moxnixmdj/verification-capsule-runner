#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"; CONFIG="default"; SPLIT="validation"
OFFSET=25; LENGTH=25; EXPECTED_TOTAL=3381
MISS=(27,32,36,37,38,39,41,43,44,45)
BASELINE_HITS=15; BASELINE_N=25; BASELINE_RUN=38145869751
SCHEMA="PROJECT_BRAIN_HLE_WIKIDATA_PRIOR_MISSES_V1"
UA="ProjectBrain-HLE-WikidataPriorMisses/1.0"

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha(x): return hashlib.sha256(canon(x)).hexdigest()

def rows():
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":LENGTH})
    for n in range(4):
        try:
            req=urllib.request.Request("https://datasets-server.huggingface.co/rows?"+q,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r: obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL: raise RuntimeError("TOTAL_MISMATCH")
            out=[]
            for z in obj["rows"]:
                idx=int(z["row_idx"])
                if idx in MISS:
                    row=z["row"]; out.append({"row_idx":idx,"question":row["question"],"answer":row["answer"]})
            out.sort(key=lambda x:x["row_idx"])
            if [x["row_idx"] for x in out]!=list(MISS): raise RuntimeError("MISS_SET_MISMATCH")
            return out
        except Exception:
            if n==3: raise
            time.sleep(2**n)

def prepare(path:Path):
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows()]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","questions":qs,"questions_manifest_sha256":sha(qs),
         "gold_written":False,"hle_questions_consumed":0}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def one(item):
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    from canonical.runtime.bound_capabilities.wikidata_entity_search_v1 import search
    p=plan_queries(task_id=item["task_id"],question=item["question"],max_views=7)
    calls=[]; candidates=[]; seen=set()
    for view in p["views"]:
        q=view["query"]
        try:
            x=search(q,limit=8,timeout=15); status=x["status"]; err=None
            for c in x["candidates"]:
                key=c["entity_id"]
                if key in seen: continue
                seen.add(key)
                candidates.append({"entity_id":key,"label":c["label"],"description":c["description"],
                                   "query":q,"method":view["method"],"rank":c["rank"]})
        except Exception as e:
            status="FAILED_RETRYABLE"; err=type(e).__name__
        calls.append({"method":view["method"],"query":q,"status":status,"error":err})
    return {"row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
            "calls":calls,"candidates":candidates,"candidate_count":len(candidates),
            "gold_accessed":False,"external_model_calls":0,"model_dependency_count":0}

def trace(qp:Path,tp:Path,workers:int):
    d=json.loads(qp.read_text()); qs=d["questions"]
    if sha(qs)!=d["questions_manifest_sha256"]: raise RuntimeError("QUESTION_MANIFEST")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(workers,3))) as pool:
        fs={pool.submit(one,x):x for x in qs}
        for f,x in fs.items():
            try: out.append(f.result())
            except Exception as e:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "calls":[],"candidates":[],"candidate_count":0,"status":"TRACE_EXCEPTION:"+type(e).__name__,
                            "gold_accessed":False,"external_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    doc={"schema":SCHEMA,"phase":"WIKIDATA_TRACE_SEALED_BEFORE_GOLD","traces":out,"trace_manifest_sha256":sha(out),
         "gold_loaded_by_trace_process":False,"external_model_calls_total":0,"model_dependency_count_total":0,
         "hle_questions_consumed":0,"hle_gold_consumed":0}
    tp.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":doc["phase"],"trace_manifest_sha256":doc["trace_manifest_sha256"],
                      "candidate_count":sum(x["candidate_count"] for x in out)},sort_keys=True))

def norm(v):
    x=unicodedata.normalize("NFKD",str(v or "")).casefold()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(x.split())

def contains(text,gold):
    t=norm(text); g=norm(gold)
    if not t or not g:return False
    if g in t:return True
    ga=re.sub(r"^(?:a|an|the)\s+","",g).strip()
    return bool(ga) and len(ga)>=4 and ga in t

def score(tp:Path,sp:Path):
    d=json.loads(tp.read_text()); traces=d["traces"]
    if sha(traces)!=d["trace_manifest_sha256"]: raise RuntimeError("TRACE_MANIFEST")
    gold={r["row_idx"]:r["answer"] for r in rows()}
    hits=[]; per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]; matches=[]
        for c in tr["candidates"]:
            if contains(c["label"],g) or contains(c["description"],g): matches.append(c["entity_id"])
        if matches:hits.append(tr["row_idx"])
        per.append({"row_idx":tr["row_idx"],"gold":g,"hit":bool(matches),"match_entity_ids":matches,
                    "candidate_count":tr["candidate_count"]})
    k=len(hits)
    out={"schema":SCHEMA,"phase":"SCORED_AFTER_TRACE_SEAL","sample_size":len(MISS),
         "wikidata_recovered_prior_misses":k,"recovered_row_indices":hits,
         "combined_union_hit_count":BASELINE_HITS+k,"combined_union_retrieval_any_hit_rate":(BASELINE_HITS+k)/BASELINE_N,
         "absolute_recall_gain":k/BASELINE_N,"external_model_calls_total":0,"model_dependency_count_total":0,
         "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,"per_slot":per}
    sp.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="per_slot"},sort_keys=True))
    for x in per: print(json.dumps(x,ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    a=s.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=s.add_parser("trace"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--trace",type=Path,required=True); a.add_argument("--workers",type=int,default=2)
    a=s.add_parser("score"); a.add_argument("--trace",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":prepare(x.questions)
    elif x.cmd=="trace":trace(x.questions,x.trace,x.workers)
    else:score(x.trace,x.summary)
if __name__=="__main__":main()
