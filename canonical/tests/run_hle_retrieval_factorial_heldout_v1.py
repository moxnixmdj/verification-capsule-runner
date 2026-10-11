#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"; CONFIG="default"; SPLIT="validation"
OFFSET=75; N=25; TARGET_IDS=list(range(75,100)); EXPECTED_TOTAL=3381
UA="ProjectBrain-HLE-RetrievalFactorial/1.0"
SCHEMA="PROJECT_BRAIN_HLE_RETRIEVAL_COMPONENT_FACTORIAL_HELDOUT_V1"

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
    rows=fetch_rows()
    qs=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
         "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","dataset":DATASET,"split":SPLIT,
         "slice":"FRESH_PUBLIC_FACTORIAL_HELDOUT_ROWS_75_TO_99","target_ids":TARGET_IDS,
         "questions_manifest_sha256":sha_obj(qs),"questions":qs,"gold_written":False,
         "budgets":{"planner_v1_max_views":5,"relation_max_queries":4,"wiki_base_queries":3,"wiki_relation_queries":2,"wiki_pages_per_query":1}}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def plan_one(item):
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    from canonical.runtime.hle_relation_requirement_compiler_v1 import compile_requirements
    base=plan_queries(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False,max_views=5)
    rel=compile_requirements(task_id=item["task_id"],question=item["question"],max_queries=4)
    b=[{"query":x["query"],"method":x.get("method"),"source":"BASELINE"} for x in base["views"]]
    seen={x["query"].casefold() for x in b};added=[]
    for x in rel.get("requirements") or []:
        q=str(x.get("query") or "").strip()
        if not q or q.casefold() in seen:continue
        seen.add(q.casefold());added.append({"query":q,"method":x.get("method"),"relation_type":x.get("relation_type"),"source":"RELATION"})
    return {"row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
            "base":b,"relation":added,"all":b+added,
            "wiki_base":b[:3],"wiki_relation":added[:2]}

def bing(q):
    from canonical.runtime.hle_native_open_domain_research_v5 import rich_search
    try:return {"status":"PASS","rows":list(rich_search(q,limit=5,timeout=15.0))}
    except Exception as e:return {"status":"FAILED_RETRYABLE:"+type(e).__name__,"rows":[]}

def wiki(q):
    from canonical.runtime.hle_wikipedia_bing_transport_v1 import retrieve
    try:
        out=retrieve(query=q,limit=1,timeout=15.0)
        if out.get("gold_accessed") is not False or int(out.get("external_model_calls",0) or 0)!=0 or int(out.get("model_dependency_count",0) or 0)!=0:
            raise RuntimeError("AUTHORITY_ACCOUNTING_FAILURE")
        return {"status":out.get("status"),"pages":out.get("pages") or []}
    except Exception as e:return {"status":"FAILED_RETRYABLE:"+type(e).__name__,"pages":[]}

def trace(qpath:Path,tpath:Path,workers:int):
    doc=json.loads(qpath.read_text());qs=doc.get("questions")
    if not isinstance(qs,list) or len(qs)!=N or sha_obj(qs)!=doc.get("questions_manifest_sha256"):raise RuntimeError("QUESTIONS_INVALID")
    plans=[plan_one(x) for x in qs]
    all_bing=[]; all_wiki=[]; sb=set(); sw=set()
    for p in plans:
        for x in p["all"]:
            k=x["query"].casefold()
            if k not in sb:sb.add(k);all_bing.append(x["query"])
        for x in p["wiki_base"]+p["wiki_relation"]:
            k=x["query"].casefold()
            if k not in sw:sw.add(k);all_wiki.append(x["query"])
    bres={};wres={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(workers),4))) as pool:
        futs={pool.submit(bing,q):("b",q) for q in all_bing}
        futs.update({pool.submit(wiki,q):("w",q) for q in all_wiki})
        for f,(kind,q) in futs.items():
            try:r=f.result()
            except Exception as e:r={"status":"FAILED_RETRYABLE:"+type(e).__name__,"rows":[],"pages":[]}
            (bres if kind=="b" else wres)[q.casefold()]=r
    traces=[]
    for p in plans:
        def bpack(spec):return [{**x,**bres[x["query"].casefold()]} for x in spec]
        def wpack(spec):return [{**x,**wres[x["query"].casefold()]} for x in spec]
        traces.append({"row_idx":p["row_idx"],"task_id":p["task_id"],"question_sha256":p["question_sha256"],
                       "base_bing":bpack(p["base"]),"relation_bing":bpack(p["relation"]),
                       "base_wiki":wpack(p["wiki_base"]),"relation_wiki":wpack(p["wiki_relation"]),
                       "relation_methods":[x.get("method") for x in p["relation"]],
                       "gold_accessed":False,"external_model_calls":0,"model_dependency_count":0})
    sealed={"schema":SCHEMA,"phase":"FOUR_ARM_TRACES_SEALED_BEFORE_GOLD","target_ids":TARGET_IDS,
            "questions_manifest_sha256":doc["questions_manifest_sha256"],"trace_manifest_sha256":sha_obj(traces),
            "bing_unique_query_count":len(all_bing),"wiki_unique_query_count":len(all_wiki),"traces":traces,
            "gold_loaded_by_trace_process":False,"external_model_calls_total":0,
            "external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    tpath.write_text(json.dumps(sealed,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":sealed["phase"],"trace_manifest_sha256":sealed["trace_manifest_sha256"],
                      "bing_unique_queries":len(all_bing),"wiki_unique_queries":len(all_wiki)},sort_keys=True))

def bing_surface(rows):
    vals=[]
    for q in rows:
        for r in q.get("rows") or []:vals.extend([str(r.get("title") or ""),str(r.get("snippet") or ""),str(r.get("url") or "")])
    return " ".join(vals)
def wiki_surface(rows):
    vals=[]
    for q in rows:
        for p in q.get("pages") or []:
            if p.get("status")=="PASS":vals.extend([str(p.get("url") or ""),str(p.get("text") or "")])
    return " ".join(vals)

def score(tpath:Path,spath:Path):
    sealed=json.loads(tpath.read_text());traces=sealed.get("traces")
    if not isinstance(traces,list) or len(traces)!=N or sha_obj(traces)!=sealed.get("trace_manifest_sha256"):raise RuntimeError("TRACE_INVALID")
    rows={r["row_idx"]:r for r in fetch_rows()}
    hitsets={k:[] for k in ["A","B","C","D"]};per=[]
    for tr in traces:
        idx=tr["row_idx"];ng=norm(rows[idx]["answer"])
        base_b=bing_surface(tr["base_bing"]); rel_b=bing_surface(tr["relation_bing"])
        base_w=wiki_surface(tr["base_wiki"]); rel_w=wiki_surface(tr["relation_wiki"])
        surfaces={"A":base_b,"B":base_b+" "+rel_b,"C":base_b+" "+base_w,"D":base_b+" "+rel_b+" "+base_w+" "+rel_w}
        hits={k:(bool(ng) and ng in norm(v)) for k,v in surfaces.items()}
        for k,v in hits.items():
            if v:hitsets[k].append(idx)
        per.append({"row_idx":idx,**{f"{k}_hit":v for k,v in hits.items()},"relation_methods":tr["relation_methods"]})
    A=set(hitsets["A"]);B=set(hitsets["B"]);C=set(hitsets["C"]);D=set(hitsets["D"])
    summary={"schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"sample_size":N,"target_ids":TARGET_IDS,
             "A_baseline_hit_ids":sorted(A),"A_hits":len(A),
             "B_relation_hit_ids":sorted(B),"B_hits":len(B),"B_unique_over_A":sorted(B-A),
             "C_wikipedia_hit_ids":sorted(C),"C_hits":len(C),"C_unique_over_A":sorted(C-A),
             "D_composition_hit_ids":sorted(D),"D_hits":len(D),"D_unique_over_A":sorted(D-A),
             "D_interaction_unique_beyond_union_B_C":sorted(D-(B|C)),
             "relation_applicable_ids":[r["row_idx"] for r in per if r["relation_methods"]],
             "per_slot":per,"external_model_calls_total":0,"external_reasoning_model_calls_total":0,
             "model_dependency_count_total":0,"hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0,
             "hard_nonclaim":"FRESH_PUBLIC_FACTORIAL_RETRIEVAL_RESULT_IS_NOT_HLE_SCORE_OR_TERMINAL_CAPABILITY_CREDIT"}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("RETRIEVAL_FACTORIAL",json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare");a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("trace");a.add_argument("--questions",type=Path,required=True);a.add_argument("--trace",type=Path,required=True);a.add_argument("--workers",type=int,default=4)
    a=sub.add_parser("score");a.add_argument("--trace",type=Path,required=True);a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare":prepare(x.questions)
    elif x.cmd=="trace":trace(x.questions,x.trace,x.workers)
    else:score(x.trace,x.summary)
if __name__=="__main__":main()
