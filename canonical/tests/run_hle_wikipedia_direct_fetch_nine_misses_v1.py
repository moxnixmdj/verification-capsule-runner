#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, html, json, re, urllib.parse
from pathlib import Path

from canonical.tests import run_hle_wikipedia_via_bing_nine_misses_v1 as base

SCHEMA="PROJECT_BRAIN_HLE_WIKIPEDIA_DIRECT_FETCH_NINE_MISSES_V1"
_TAG=re.compile(r"<[^>]+>")

def clean_html(v:str)->str:
    return " ".join(html.unescape(_TAG.sub(" ",str(v or ""))).split())

def trace_one(item):
    from canonical.runtime import hle_native_retrieval_query_planner_v1 as planner
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search
    from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools

    plan=planner.plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7)
    discovered=[]
    search_receipts=[]
    seen=set()
    for vi,v in enumerate(plan.get("views") or [],1):
        q=" ".join(str(v.get("query") or "").split())
        query="site:en.wikipedia.org "+q
        try:
            rows=list(rich_search(query,limit=5)); status="PASS"
        except Exception as exc:
            rows=[]; status="FAILED:"+type(exc).__name__
        accepted=0
        for x in rows:
            url=str(x.get("url") or "")
            try:
                host=(urllib.parse.urlparse(url).hostname or "").lower()
            except Exception:
                host=""
            if not (host=="en.wikipedia.org" or host.endswith(".wikipedia.org")):
                continue
            if url in seen: continue
            seen.add(url); accepted+=1
            discovered.append({
                "view":vi,
                "rank":int(x.get("rank") or 99),
                "url":url,
                "title":str(x.get("title") or ""),
                "snippet":str(x.get("snippet") or ""),
            })
        search_receipts.append({"view":vi,"method":v.get("method"),"query_sha256":hashlib.sha256(query.encode()).hexdigest(),
                                "status":status,"wikipedia_url_count":accepted})
    discovered.sort(key=lambda x:(x["view"],x["rank"],x["url"]))
    pages=[]; fetch_receipts=[]
    for row in discovered[:6]:
        try:
            out=tools.fetch_web(row["url"],max_bytes=500000)
            status=str(out.get("status") or "UNKNOWN")
            text=clean_html(str(out.get("body_excerpt") or ""))
            pages.append({"url":row["url"],"title":row["title"],"text":text})
            fetch_receipts.append({"url_sha256":hashlib.sha256(row["url"].encode()).hexdigest(),
                                   "status":status,"http_status":out.get("http_status"),"text_chars":len(text)})
        except Exception as exc:
            fetch_receipts.append({"url_sha256":hashlib.sha256(row["url"].encode()).hexdigest(),
                                   "status":"FAILED:"+type(exc).__name__,"http_status":getattr(exc,"code",None),"text_chars":0})
    return {
        "row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
        "search_records":[{"title":x["title"],"snippet":x["snippet"],"url":x["url"]} for x in discovered],
        "page_records":pages,
        "search_receipts":search_receipts,
        "fetch_receipts":fetch_receipts,
        "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0,
    }

def prepare(path:Path):
    base.prepare(path)

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
                            "search_records":[],"page_records":[],"search_receipts":[],"fetch_receipts":[],
                            "trace_exception":type(exc).__name__,"gold_accessed":False,
                            "external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0})
    out.sort(key=lambda x:x["row_idx"])
    doc={"schema":SCHEMA,"phase":"DIRECT_PAGE_TRACES_SEALED_BEFORE_GOLD","target_ids":base.TARGET_IDS,
         "questions_manifest_sha256":qdoc["questions_manifest_sha256"],"trace_manifest_sha256":base.sha_obj(out),
         "traces":out,"gold_loaded_by_trace_process":False,"external_model_calls_total":0,
         "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":doc["phase"],"trace_manifest_sha256":doc["trace_manifest_sha256"],
                      "page_fetches":sum(len(x["fetch_receipts"]) for x in out)},sort_keys=True))

def score(tpath:Path,spath:Path):
    td=json.loads(tpath.read_text()); traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=len(base.TARGET_IDS) or base.sha_obj(traces)!=td.get("trace_manifest_sha256"):
        raise RuntimeError("TRACE_INVALID")
    gold={r["row_idx"]:r["answer"] for r in base.fetch_rows()}
    snippet_hits=[]; page_hits=[]; page_unique=[]; union=[]; fetch_status={}
    per=[]
    for tr in traces:
        g=gold[tr["row_idx"]]
        sh=any(base.contains(str(x.get("title") or ""),g) or base.contains(str(x.get("snippet") or ""),g)
               for x in tr.get("search_records") or [])
        ph=any(base.contains(str(x.get("title") or ""),g) or base.contains(str(x.get("text") or ""),g)
               for x in tr.get("page_records") or [])
        if sh: snippet_hits.append(tr["row_idx"])
        if ph: page_hits.append(tr["row_idx"])
        if ph and not sh: page_unique.append(tr["row_idx"])
        if sh or ph: union.append(tr["row_idx"])
        for r in tr.get("fetch_receipts") or []:
            k=str(r.get("status") or "UNKNOWN"); fetch_status[k]=fetch_status.get(k,0)+1
        per.append({"row_idx":tr["row_idx"],"site_snippet_hit":sh,"direct_page_hit":ph,
                    "page_fetch_count":len(tr.get("fetch_receipts") or [])})
    summary={"schema":SCHEMA,"target_ids":base.TARGET_IDS,"sample_size":len(base.TARGET_IDS),
             "site_snippet_hit_ids":snippet_hits,"site_snippet_hit_count":len(snippet_hits),
             "direct_page_hit_ids":page_hits,"direct_page_hit_count":len(page_hits),
             "direct_page_unique_hit_ids":page_unique,"direct_page_unique_hit_count":len(page_unique),
             "union_hit_ids":union,"union_hit_count":len(union),
             "remaining_miss_ids":[i for i in base.TARGET_IDS if i not in union],
             "fetch_status_counts":fetch_status,"per_slot":per,
             "external_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("DIRECT_WIKI_RESULT",json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

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
