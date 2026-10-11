#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"; CONFIG="default"; SPLIT="validation"
OFFSET=25; WINDOW_N=25; MISS_ROWS={27,29,32,35,36,37,38,39,41,43,44,45}; N=len(MISS_ROWS); EXPECTED_TOTAL=3381
UA="ProjectBrain-HLE-RetrievalTrace-QueryPlannerV2-Misses/1.0"
SCHEMA="PROJECT_BRAIN_HLE_RETRIEVAL_TRACE_QUERY_PLANNER_V2_MISSES_V1"

def canon_obj(x:Any)->bytes:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha_obj(x:Any)->str:return hashlib.sha256(canon_obj(x)).hexdigest()
def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":WINDOW_N})
    url="https://datasets-server.huggingface.co/rows?"+q
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r:obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=WINDOW_N:raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j; row=item.get("row") or {}
                if int(item.get("row_idx",-1))!=idx:raise RuntimeError("ORDER_MISMATCH")
                qv=row.get("question");av=row.get("answer")
                if not isinstance(qv,str) or not qv.strip() or not isinstance(av,str) or not av.strip():raise RuntimeError("ROW_INVALID")
                if idx not in MISS_ROWS: continue
                out.append({"row_idx":idx,"question":qv,"answer":av})
            return out
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","rows":N,
         "slice":"V1_SHARED_MISSES_ONLY__ROWS_27_29_32_35_36_37_38_39_41_43_44_45__ALREADY_CONSUMED","questions_manifest_sha256":sha_obj(qs),
         "questions":qs,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_retrieval_query_planner_v2 import plan_queries
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search,wikipedia_search,wikipedia_extracts
    c=plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7)
    views=list(c.get("views") or [])[:7]
    records=[]; pageids={}
    for vi,v in enumerate(views,1):
        query=str(v.get("query") or "")
        try: rr=list(rich_search(query,limit=8)); rs="PASS"
        except Exception as e: rr=[];rs="FAILED:"+type(e).__name__
        for row in rr:
            records.append({"source":"BING_RSS","view":vi,"query":query,
                            "rank":int(row.get("rank") or 99),"title":str(row.get("title") or ""),
                            "snippet":str(row.get("snippet") or ""),"url":str(row.get("url") or "")})
        try: wr=list(wikipedia_search(query,limit=8)); ws="PASS"
        except Exception as e: wr=[];ws="FAILED:"+type(e).__name__
        for row in wr:
            pid=int(row.get("pageid") or 0)
            if pid>0:pageids[pid]=str(row.get("title") or "")
            records.append({"source":"WIKIPEDIA_SEARCH","view":vi,"query":query,
                            "rank":int(row.get("rank") or 99),"title":str(row.get("title") or ""),
                            "snippet":str(row.get("snippet") or ""),"pageid":pid})
    pids=list(pageids)[:28]
    try: ex=wikipedia_extracts(pids) if pids else {}
    except Exception: ex={}
    for pid in pids:
        records.append({"source":"WIKIPEDIA_EXTRACT","view":0,"query":"","rank":0,
                        "title":pageids[pid],"snippet":str(ex.get(pid,""))[:6000],"pageid":pid})
    return {"row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
            "question_kind":c.get("question_kind"),"answer_subtype":c.get("answer_subtype"),
            "views":[{"method":v.get("method"),"query":v.get("query"),"query_sha256":v.get("query_sha256")} for v in views],
            "records":records,"record_count":len(records),"gold_accessed":False,
            "external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0}

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text());qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=N or sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fs={pool.submit(trace_one,x):x for x in qs}
        for f,x in fs.items():
            try:out.append(f.result())
            except Exception as e:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "question_kind":None,"answer_subtype":None,"views":[],"records":[],"record_count":0,
                            "status":"TRACE_EXCEPTION:"+type(e).__name__,"gold_accessed":False,
                            "external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0})
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
    t=norm(text);g=norm(gold)
    if not t or not g:return False
    if g in t:return True
    # article-insensitive answer surface
    ga=re.sub(r"^(?:a|an|the)\s+","",g).strip()
    return bool(ga) and len(ga)>=4 and ga in t

def score(qpath:Path,tpath:Path,spath:Path)->None:
    td=json.loads(tpath.read_text()); traces=td.get("traces")
    if not isinstance(traces,list) or len(traces)!=N or sha_obj(traces)!=td.get("trace_manifest_sha256"):raise RuntimeError("TRACE_INVALID")
    rows=fetch_rows();gold={r["row_idx"]:r["answer"] for r in rows}
    per=[];any_n=rich_n=wst_n=wss_n=wex_n=0
    for tr in traces:
        g=gold[tr["row_idx"]]; rich=wt=ws=we=False; exact_title=[]
        for r in tr.get("records") or []:
            src=r.get("source");title=str(r.get("title") or "");snip=str(r.get("snippet") or "")
            hit_t=contains(title,g);hit_s=contains(snip,g)
            if src=="BING_RSS": rich=rich or hit_t or hit_s
            elif src=="WIKIPEDIA_SEARCH":
                wt=wt or hit_t; ws=ws or hit_s
                if norm(title)==norm(g) or re.sub(r"^(?:a|an|the)\s+","",norm(title))==re.sub(r"^(?:a|an|the)\s+","",norm(g)):
                    exact_title.append(title)
            elif src=="WIKIPEDIA_EXTRACT": we=we or hit_t or hit_s
        anyhit=rich or wt or ws or we
        any_n+=int(anyhit);rich_n+=int(rich);wst_n+=int(wt);wss_n+=int(ws);wex_n+=int(we)
        per.append({"row_idx":tr["row_idx"],"question_kind":tr.get("question_kind"),"answer_subtype":tr.get("answer_subtype"),
                    "gold":g,"retrieval_any_hit":anyhit,"rich_hit":rich,"wiki_title_hit":wt,
                    "wiki_snippet_hit":ws,"wiki_extract_hit":we,"wiki_exact_title_matches":exact_title,
                    "record_count":tr.get("record_count",0),
                    "queries":[v.get("query") for v in tr.get("views") or []]})
    summary={"schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"sample_size":N,
             "slice":"V1_SHARED_MISSES_ONLY__ROWS_27_29_32_35_36_37_38_39_41_43_44_45__ALREADY_CONSUMED",
             "retrieval_any_hit":any_n,"retrieval_any_hit_rate":any_n/N,
             "rich_hit":rich_n,"rich_hit_rate":rich_n/N,
             "wiki_title_hit":wst_n,"wiki_title_hit_rate":wst_n/N,
             "wiki_snippet_hit":wss_n,"wiki_snippet_hit_rate":wss_n/N,
             "wiki_extract_hit":wex_n,"wiki_extract_hit_rate":wex_n/N,
             "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,"per_slot":per}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))
    for r in per:print(json.dumps(r,ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare");a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace");a.add_argument("--questions",type=Path,required=True);a.add_argument("--trace",type=Path,required=True);a.add_argument("--workers",type=int,default=4)
    a=sub.add_parser("score");a.add_argument("--questions",type=Path,required=True);a.add_argument("--trace",type=Path,required=True);a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":prepare(x.questions)
    elif x.cmd=="trace":trace(x.questions,x.trace,x.workers)
    else:score(x.questions,x.trace,x.summary)
if __name__=="__main__":main()
