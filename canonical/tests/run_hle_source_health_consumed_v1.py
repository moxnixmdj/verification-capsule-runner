#!/usr/bin/env python3
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_HLE_SOURCE_HEALTH_CONSUMED_V1"

def one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search,wikipedia_search
    p=plan_queries(task_id=item["task_id"],question=item["question"],max_views=7)
    rows=[]
    for v in p["views"]:
        q=v["query"]
        rec={"query_sha256":hashlib.sha256(q.encode()).hexdigest(),"method":v["method"]}
        try:
            x=rich_search(q,limit=8)
            rec["bing_status"]="PASS";rec["bing_count"]=len(x)
        except Exception as e:
            rec["bing_status"]="EXCEPTION:"+type(e).__name__;rec["bing_count"]=0
        try:
            x=wikipedia_search(q,limit=8)
            rec["wiki_status"]="PASS";rec["wiki_count"]=len(x)
        except Exception as e:
            rec["wiki_status"]="EXCEPTION:"+type(e).__name__;rec["wiki_count"]=0
        rows.append(rec)
    return {"row_idx":item["row_idx"],"rows":rows,"external_model_calls":0,"model_dependency_count":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--questions",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--workers",type=int,required=True)
    a=p.parse_args()
    qdoc=json.loads(a.questions.read_text()); qs=qdoc["questions"]
    out=[]
    if a.workers<=1:
        out=[one(x) for x in qs]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            out=list(pool.map(one,qs))
    bc=Counter();wc=Counter();bn=wn=0;calls=0
    for item in out:
        for r in item["rows"]:
            calls+=1;bc[r["bing_status"]]+=1;wc[r["wiki_status"]]+=1
            bn+=int(r["bing_count"]>0);wn+=int(r["wiki_count"]>0)
    doc={"schema":SCHEMA,"workers":a.workers,"query_calls":calls,
         "bing_status_counts":dict(bc),"wiki_status_counts":dict(wc),
         "bing_nonempty_calls":bn,"wiki_nonempty_calls":wn,
         "bing_nonempty_rate":bn/calls if calls else 0.0,
         "wiki_nonempty_rate":wn/calls if calls else 0.0,
         "external_model_calls_total":0,"model_dependency_count_total":0,
         "hle_questions_consumed":0,"hle_gold_consumed":0,"rows":out}
    a.out.write_text(json.dumps(doc,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="rows"},sort_keys=True))
if __name__=="__main__":main()
