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
TARGET_IDS=[27,29,32,35,36,37,38,39,41,43,44,45]
UA="ProjectBrain-HLE-QueryPlannerV2-PairedMisses/1.0"
SCHEMA="PROJECT_BRAIN_HLE_QUERY_PLANNER_V2_PAIRED_MISSES_V1"

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
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:
                raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N:
                raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j
                if idx not in TARGET_IDS:
                    continue
                if int(item.get("row_idx",-1))!=idx:
                    raise RuntimeError("ORDER_MISMATCH")
                row=item.get("row") or {}
                question=row.get("question"); answer=row.get("answer")
                if not isinstance(question,str) or not question.strip() or not isinstance(answer,str) or not answer.strip():
                    raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":question,"answer":answer})
            if [x["row_idx"] for x in out]!=TARGET_IDS:
                raise RuntimeError("TARGET_ID_SET_MISMATCH")
            return out
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)
    raise RuntimeError("FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    qs=[{
        "row_idx":r["row_idx"],
        "task_id":f"triviaqa_validation_row_{r['row_idx']}",
        "question":r["question"],
        "question_sha256":hashlib.sha256(r["question"].encode()).hexdigest(),
    } for r in rows]
    doc={
        "schema":SCHEMA,
        "phase":"QUESTIONS_ONLY_PREPARED",
        "dataset":DATASET,
        "split":SPLIT,
        "target_ids":TARGET_IDS,
        "rows":len(qs),
        "questions_manifest_sha256":sha_obj(qs),
        "questions":qs,
        "gold_written":False,
    }
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def _plans(item:dict[str,Any])->dict[str,dict[str,Any]]:
    from canonical.runtime import hle_native_retrieval_query_planner_v1 as p1
    from canonical.runtime import hle_native_retrieval_query_planner_v2 as p2
    return {
        "v1":p1.plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7),
        "v2":p2.plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=7),
    }

def trace_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search,wikipedia_search,wikipedia_extracts
    plans=_plans(item)
    queries={}
    for label,plan in plans.items():
        for vi,v in enumerate(plan.get("views") or [],1):
            q=" ".join(str(v.get("query") or "").split())
            if q:
                queries.setdefault(q.casefold(),{"query":q,"users":[]})["users"].append((label,vi,str(v.get("method") or "UNKNOWN")))
    fetched={}
    for key,row in queries.items():
        q=row["query"]
        try:
            rr=list(rich_search(q,limit=8)); rs="PASS"
        except Exception as exc:
            rr=[]; rs="FAILED:"+type(exc).__name__
        try:
            wr=list(wikipedia_search(q,limit=8)); ws="PASS"
        except Exception as exc:
            wr=[]; ws="FAILED:"+type(exc).__name__
        fetched[key]={
            "query":q,
            "rich_status":rs,
            "wiki_status":ws,
            "rich":[{
                "title":str(x.get("title") or ""),
                "snippet":str(x.get("snippet") or ""),
                "url":str(x.get("url") or ""),
                "rank":int(x.get("rank") or 99),
            } for x in rr],
            "wiki":[{
                "pageid":int(x.get("pageid") or 0),
                "title":str(x.get("title") or ""),
                "snippet":str(x.get("snippet") or ""),
                "rank":int(x.get("rank") or 99),
            } for x in wr],
        }

    selected={}
    for label,plan in plans.items():
        pids={}
        qkeys=[str(v.get("query") or "").strip().casefold() for v in plan.get("views") or []]
        for vi,key in enumerate(qkeys,1):
            row=fetched.get(key) or {}
            for x in row.get("wiki") or []:
                pid=int(x.get("pageid") or 0)
                if pid<=0: continue
                cand=(int(x.get("rank") or 99),vi,str(x.get("title") or ""))
                if pid not in pids or cand<pids[pid]:
                    pids[pid]=cand
        selected[label]=[pid for pid,_ in sorted(pids.items(),key=lambda kv:kv[1])[:24]]

    union_pids=[]
    for label in ("v1","v2"):
        for pid in selected[label]:
            if pid not in union_pids: union_pids.append(pid)
    extracts={}
    for start in range(0,len(union_pids),30):
        chunk=union_pids[start:start+30]
        try:
            extracts.update(wikipedia_extracts(chunk))
        except Exception:
            pass

    records={}
    receipts={}
    for label,plan in plans.items():
        rec=[]; rc=[]
        for vi,v in enumerate(plan.get("views") or [],1):
            q=str(v.get("query") or "").strip(); key=q.casefold(); row=fetched.get(key) or {}
            rc.append({
                "view":vi,
                "method":str(v.get("method") or "UNKNOWN"),
                "query_sha256":str(v.get("query_sha256") or ""),
                "rich_status":row.get("rich_status"),
                "rich_count":len(row.get("rich") or []),
                "wiki_status":row.get("wiki_status"),
                "wiki_count":len(row.get("wiki") or []),
            })
            for x in row.get("rich") or []:
                rec.append({"source":"BING_RSS","view":vi,"title":x["title"],"snippet":x["snippet"],"url":x["url"]})
            for x in row.get("wiki") or []:
                rec.append({"source":"WIKIPEDIA_SEARCH","view":vi,"title":x["title"],"snippet":x["snippet"],"pageid":x["pageid"]})
        title_by_pid={}
        rank_by_pid={}
        for vi,v in enumerate(plan.get("views") or [],1):
            row=fetched.get(str(v.get("query") or "").strip().casefold()) or {}
            for x in row.get("wiki") or []:
                pid=int(x.get("pageid") or 0)
                if pid<=0: continue
                title_by_pid.setdefault(pid,x["title"])
                rank_by_pid[pid]=min(rank_by_pid.get(pid,99),int(x.get("rank") or 99))
        for pid in selected[label]:
            rec.append({
                "source":"WIKIPEDIA_EXTRACT",
                "view":0,
                "title":title_by_pid.get(pid,""),
                "snippet":str(extracts.get(pid,""))[:6000],
                "pageid":pid,
                "rank":rank_by_pid.get(pid,99),
            })
        records[label]=rec
        receipts[label]=rc

    return {
        "row_idx":item["row_idx"],
        "task_id":item["task_id"],
        "question_sha256":item["question_sha256"],
        "plans":{
            label:{
                "schema":plan.get("schema"),
                "view_count":plan.get("view_count"),
                "views":[{
                    "method":v.get("method"),
                    "query_sha256":v.get("query_sha256"),
                    "query":v.get("query"),
                } for v in plan.get("views") or []],
            } for label,plan in plans.items()
        },
        "records":records,
        "receipts":receipts,
        "unique_query_count":len(queries),
        "gold_accessed":False,
        "external_model_calls":0,
        "external_reasoning_model_calls":0,
        "model_dependency_count":0,
    }

def trace(qpath:Path,tpath:Path,workers:int)->None:
    qdoc=json.loads(qpath.read_text()); qs=qdoc.get("questions")
    if not isinstance(qs,list) or len(qs)!=len(TARGET_IDS) or sha_obj(qs)!=qdoc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(workers,3))) as pool:
        futs={pool.submit(trace_one,x):x for x in qs}
        for f,x in futs.items():
            try:
                out.append(f.result())
            except Exception as exc:
                out.append({
                    "row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                    "trace_exception":type(exc).__name__,"plans":{},"records":{"v1":[],"v2":[]},"receipts":{"v1":[],"v2":[]},
                    "unique_query_count":0,"gold_accessed":False,"external_model_calls":0,
                    "external_reasoning_model_calls":0,"model_dependency_count":0,
                })
    out.sort(key=lambda x:x["row_idx"])
    doc={
        "schema":SCHEMA,
        "phase":"PAIRED_RETRIEVAL_TRACES_SEALED_BEFORE_GOLD",
        "target_ids":TARGET_IDS,
        "trace_count":len(out),
        "questions_manifest_sha256":qdoc["questions_manifest_sha256"],
        "trace_manifest_sha256":sha_obj(out),
        "traces":out,
        "gold_loaded_by_trace_process":False,
        "external_model_calls_total":0,
        "external_reasoning_model_calls_total":0,
        "model_dependency_count_total":0,
    }
    tpath.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "phase":doc["phase"],
        "trace_manifest_sha256":doc["trace_manifest_sha256"],
        "trace_count":len(out),
        "unique_queries":sum(x.get("unique_query_count",0) for x in out),
    },sort_keys=True))

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
    counts={"v1":0,"v2":0}; v2_unique=[]; v1_unique=[]; union=[]; per=[]
    for tr in traces:
        idx=tr["row_idx"]; g=gold[idx]; hits={}
        for label in ("v1","v2"):
            hit=False
            for r in (tr.get("records") or {}).get(label,[]):
                if contains(str(r.get("title") or ""),g) or contains(str(r.get("snippet") or ""),g):
                    hit=True; break
            hits[label]=hit; counts[label]+=int(hit)
        if hits["v2"] and not hits["v1"]: v2_unique.append(idx)
        if hits["v1"] and not hits["v2"]: v1_unique.append(idx)
        if hits["v1"] or hits["v2"]: union.append(idx)
        per.append({"row_idx":idx,"v1_hit":hits["v1"],"v2_hit":hits["v2"]})
    summary={
        "schema":SCHEMA,
        "dataset":DATASET,
        "split":SPLIT,
        "target_ids":TARGET_IDS,
        "sample_size":len(TARGET_IDS),
        "v1_hits":counts["v1"],
        "v1_hit_rate":counts["v1"]/len(TARGET_IDS),
        "v2_hits":counts["v2"],
        "v2_hit_rate":counts["v2"]/len(TARGET_IDS),
        "v2_unique_hit_ids":v2_unique,
        "v2_unique_hit_count":len(v2_unique),
        "v1_unique_hit_ids":v1_unique,
        "v1_unique_hit_count":len(v1_unique),
        "union_hit_ids":union,
        "union_hit_count":len(union),
        "union_hit_rate":len(union)/len(TARGET_IDS),
        "remaining_shared_miss_ids":[i for i in TARGET_IDS if i not in union],
        "per_slot":per,
        "external_model_calls_total":0,
        "external_reasoning_model_calls_total":0,
        "model_dependency_count_total":0,
        "hle_questions_consumed":0,
        "hle_gold_consumed":0,
        "hle_score_credit":0,
    }
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("PAIRED_RESULT",json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--trace",type=Path,required=True); a.add_argument("--workers",type=int,default=2)
    a=sub.add_parser("score"); a.add_argument("--trace",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare": prepare(x.questions)
    elif x.cmd=="trace": trace(x.questions,x.trace,x.workers)
    else: score(x.trace,x.summary)
if __name__=="__main__":
    main()
