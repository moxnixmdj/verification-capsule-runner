#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr510_ind_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

discovery=load("open_web_source_candidate_discovery")
frontend=load("open_research_source_frontend")
relevance=load("objective_relevance_bm25")
decomp=load("broad_objective_decompose")

fail=[]
cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond:
        fail.append(label)

query_cases=[
    (
      "Evaluate whether RFC 9110 obsoletes RFC 7230. Use authoritative primary technical evidence and independently verify the result.",
      "RFC 9110 obsoletes RFC 7230",
    ),
    (
      "Assess whether Python 3.13.7 is newer than Python 3.12.11. Preserve provenance and verify the consequential result.",
      "Python 3.13.7 is newer than Python 3.12.11",
    ),
    (
      "Compare annual mean discharge of River Alpha with River Beta. Report material limitations and independently verify the comparison.",
      "annual mean discharge of River Alpha with River Beta",
    ),
]
for i,(objective,expected) in enumerate(query_cases):
    got=discovery._query(objective)
    check(f"query_case_{i}",got==expected,{"got":got,"expected":expected})

explicit="RFC 9110 HTTP semantics official specification"
check("explicit_query_preserved",discovery._query(explicit)==explicit,discovery._query(explicit))
unrecognized="Please assess whether RFC 9110 changed HTTP semantics"
check("unrecognized_wrapper_preserved",discovery._query(unrecognized)==unrecognized,discovery._query(unrecognized))

objective=(
    "Assess whether RFC 9110 obsoletes RFC 7230. Use authoritative primary technical "
    "evidence and a real executable check. Independently verify the consequential result."
)
focused=discovery._query(objective)
candidates=[
    {
      "url":"https://noise.example/assess",
      "host":"noise.example",
      "title":"How to assess evidence quality",
      "snippet":"Assess authoritative evidence and verification quality.",
    },
    {
      "url":"https://standards.example/rfc9110",
      "host":"standards.example",
      "title":"RFC 9110 HTTP Semantics",
      "snippet":"RFC 9110 obsoletes RFC 7230 and defines HTTP semantics.",
    },
]
original=frontend._load_sibling
class Discovery:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","objective":objective,"query":focused,"candidates":candidates}
class Provenance:
    @staticmethod
    def verify(candidate,timeout=15):
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":candidate["url"],"final_host":candidate["host"]}
class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"AUTHORITY_UNRESOLVED","reason":"INDEPENDENT_FIXTURE"}
class Extractor:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15):
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"QUALIFIER_STOPS_AFTER_SOURCE_SELECTION","source_url":candidate["url"]}
class Binder:
    @staticmethod
    def bind(*args,**kwargs):
        raise AssertionError("BINDER_MUST_NOT_RUN")
def fake(name):
    return {
      "open_web_source_candidate_discovery":Discovery,
      "source_candidate_provenance_verify":Provenance,
      "objective_relevance_bm25":relevance,
      "objective_evidence_unit_extract":Extractor,
      "objective_claim_operand_binding":Binder,
      "source_authority_binding_ror":Authority,
    }[name]
frontend._load_sibling=fake
try:
    d=decomp.decompose(objective)
    check("decomposition_ready",d.get("status")=="DECOMPOSED",d)
    out=frontend.run(objective,d,limit=4,timeout=2)
finally:
    frontend._load_sibling=original
check("frontend_binds_focused_relevance_query",out.get("relevance_query")==focused,out.get("relevance_query"))
selected=((out.get("objective_relevance_verifications") or [{}])[0].get("candidate") or {})
check("focused_relevance_selects_subject",selected.get("url")=="https://standards.example/rfc9110",selected)

live_objective=(
    "Assess whether RFC 9110 defines HTTP semantics. Use authoritative primary technical "
    "evidence, preserve provenance, and independently verify the result."
)
live=discovery.discover(live_objective,limit=12,timeout=20)
live_query=discovery._query(live_objective)
check("live_query_bound",live.get("query")==live_query,{"query":live.get("query"),"expected":live_query})
check("live_candidates_present",live.get("status")=="CANDIDATES_DISCOVERED" and int(live.get("candidate_count") or 0)>0,live)
hay="\n".join(" ".join(str(c.get(k) or "") for k in ("url","title","snippet")).lower() for c in (live.get("candidates") or []))
check("live_candidates_reach_subject","9110" in hay and ("http" in hay or "semantics" in hay),{"query":live_query,"hay":hay[:4000]})

report={
  "schema":"BRAIN_PR510_QUERY_RELEVANCE_FOCUS_INDEPENDENT_QUALIFICATION_V1",
  "status":"PASS" if not fail else "FAIL",
  "brain_pr":510,
  "brain_head_sha":"135bb413448cb9a0c2fc1f39943d1cd800fbb9ef",
  "candidate_blobs":{
    "discovery":"c913c20203b638caff050e7461a4b0023852ee10",
    "frontend":"a6fa0f32eab09791ec6a8cdabe961519d073be58",
    "relevance":"95d2b6bac6f6ffb5db97526407fcd22cbcc6c790",
    "decomposer":"3ded762075ed222228a14877af631f1e2e6d9e4c"
  },
  "failures":fail,
  "cases":cases,
  "parent_task_execution":False,
  "parent_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0
}
(ROOT/"pr510-independent-query-relevance-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
