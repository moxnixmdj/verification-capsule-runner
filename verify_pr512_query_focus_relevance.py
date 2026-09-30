#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent

def load(rel,name):
    p=ROOT/rel
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

focus=load("canonical/runtime/bound_capabilities/research_query_focus.py","pr512_focus")
ranker=load("canonical/runtime/bound_capabilities/objective_relevance_bm25.py","pr512_rank")

cases=[
("GENOMICS",
 "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 is greater than the human mitochondrial reference genome sequence length. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant primary records, choose and run a zero-cost verification method, identify limitations, independently verify the result, and produce a decision-quality answer with provenance.",
 ["escherichia","coli","mg1655","human","mitochondrial","genome","sequence","length"],
 ["assess","authoritative","autonomously","verification","provenance"]),
("NETWORK",
 "Determine whether the maximum permitted HTTP/2 initial stream flow-control window exceeds the default initial stream flow-control window. Use authoritative technical evidence and independently verify the result.",
 ["http/2","flow-control","window","maximum","default"],
 ["determine","authoritative","verify"]),
("MATERIALS",
 "Evaluate whether nickel alloy tensile strength at 650 C is lower than tensile strength at 20 C. Use authoritative technical evidence and a real executable check.",
 ["nickel","alloy","tensile","strength","650","20"],
 ["evaluate","authoritative","executable"]),
]

reports=[]
for label,obj,required,forbidden in cases:
    out=focus.focus(obj)
    if out.get("status")!="FOCUSED": raise AssertionError((label,"NOT_FOCUSED",out))
    q=out["query"].lower()
    for x in required:
        if x not in q: raise AssertionError((label,"MISSING",x,q))
    for x in forbidden:
        if x in q: raise AssertionError((label,"CONTROL_LEAK",x,q))
    if out.get("model_dependency_count")!=0: raise AssertionError((label,"MODEL_DEP"))
    reports.append({"case":label,"query":out["query"],"status":"PASS"})

genomics=cases[0][1]
candidates=[
 {"url":"https://bad.example/asess","title":"Asess or Assess? Correct spelling","snippet":"How to spell assess and use assessment."},
 {"url":"https://seq.example/ecoli","title":"Escherichia coli K-12 MG1655 complete genome sequence","snippet":"Complete genome sequence and reference length for E. coli K-12 MG1655."},
 {"url":"https://seq.example/mt","title":"Human mitochondrial reference genome sequence","snippet":"Human mitochondrial genome reference sequence and sequence length."},
]
r=ranker.rank(genomics,candidates)
if r.get("status")!="LEXICAL_RELEVANCE_RANKED": raise AssertionError(("GENOMICS_RANK_FAIL",r))
if r.get("top_candidate_original_index")==0: raise AssertionError(("SPELLING_PAGE_WON",r))
bad=next(x for x in r["ranked_candidates"] if x["original_index"]==0)
if bad.get("matched_terms"): raise AssertionError(("SPELLING_PAGE_MATCHED_SUBJECT",bad,r.get("query_tokens")))
if r.get("semantic_entailment_status")!="UNVERIFIED" or r.get("factual_correctness_status")!="UNVERIFIED":
    raise AssertionError(("CLAIM_INFLATION",r))

network=cases[1][1]
r2=ranker.rank(network,[
 {"url":"https://bad.example/assessment","title":"Technical skills assessment","snippet":"How to assess employee skills."},
 {"url":"https://proto.example/http2","title":"HTTP/2 flow control window","snippet":"HTTP/2 initial stream flow control default and maximum window."},
])
if r2.get("top_candidate_original_index")!=1: raise AssertionError(("NETWORK_WRONG_TOP",r2))

report={
 "schema":"PROJECT_BRAIN_PR512_QUERY_FOCUS_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":512,
 "producer_blobs":{
   "research_query_focus":"ed84275624182c6cc1676b93f4b1b79c08c91bad",
   "open_web_source_candidate_discovery":"045369d8cba5680c60b57e834d09d12a54d94380",
   "objective_relevance_bm25":"a25a34d879413a9853f1d1ffd8ef5e4f6bdd2245",
 },
 "cases":reports,
 "genomics_replay":False,
 "parent_task_execution":False,
 "semantic_entailment_verified":False,
 "factual_correctness_verified":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0,
}
(ROOT/"pr512-query-focus-relevance-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
