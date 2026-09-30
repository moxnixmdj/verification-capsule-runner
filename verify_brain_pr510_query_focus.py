#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_pr510_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

discovery=load("open_web_source_candidate_discovery")
frontend=load("open_research_source_frontend")
relevance=load("objective_relevance_bm25")

goal=(
    "Determine whether Mars equatorial radius is greater than Mercury equatorial radius. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify the relevant records, choose and run a zero-cost "
    "verification method, identify material limitations, and preserve provenance."
)
focused=discovery._query(goal)
assert focused=="Mars equatorial radius is greater than Mercury equatorial radius", focused
for forbidden in ("Determine whether","authoritative","zero-cost","provenance"):
    assert forbidden.lower() not in focused.lower(), (forbidden,focused)
assert discovery._query("RFC 9110 HTTP semantics official specification")=="RFC 9110 HTTP semantics official specification"
abbr=discovery._query(
    "Assess whether E. coli growth rate exceeds B. subtilis growth rate. "
    "Use authoritative experimental evidence."
)
assert abbr=="E. coli growth rate exceeds B. subtilis growth rate", abbr

candidates=[
    {
      "url":"https://noise.example/determine",
      "host":"noise.example",
      "title":"Determine definition and examples",
      "snippet":"Determine means assess, decide, evaluate and verify.",
    },
    {
      "url":"https://science.example/planetary-radii",
      "host":"science.example",
      "title":"Mars and Mercury equatorial radius reference data",
      "snippet":"Mars equatorial radius Mercury equatorial radius planetary reference records.",
    },
]

class D:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {
          "status":"CANDIDATES_DISCOVERED",
          "objective":objective,
          "query":focused,
          "query_strategy":"INDEPENDENT_FIXTURE",
          "candidates":candidates,
        }

class P:
    @staticmethod
    def verify(candidate,timeout=15):
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],
          "final_url":candidate["url"],
          "final_host":candidate["host"],
        }

class A:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"OPTIONAL_METADATA_ONLY"}

class E:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15):
        return {
          "status":"EVIDENCE_EXTRACTION_BLOCKED",
          "reason":"INDEPENDENT_TEST_STOPS_AFTER_SELECTION",
          "source_url":candidate["url"],
        }

class B:
    @staticmethod
    def bind(*args,**kwargs):
        raise AssertionError("BINDER_MUST_NOT_RUN_WITHOUT_EXTRACTED_EVIDENCE")

original=frontend._load_sibling
frontend._load_sibling=lambda name:{
    "open_web_source_candidate_discovery":D,
    "source_candidate_provenance_verify":P,
    "objective_relevance_bm25":relevance,
    "objective_evidence_unit_extract":E,
    "objective_claim_operand_binding":B,
    "source_authority_binding_ror":A,
}[name]
try:
    decomposition={
      "status":"DECOMPOSED",
      "objective":goal,
      "question_shape":"COMPARATIVE",
      "roles":[{"role":"SOURCE_DISCOVERY"}],
    }
    out=frontend.run(goal,decomposition,limit=4,timeout=2)
finally:
    frontend._load_sibling=original

assert out["relevance_query"]==focused, out
selected=out["objective_relevance_verifications"][0]["candidate"]
assert selected["url"]=="https://science.example/planetary-radii", out
ranked=out["objective_relevance_verifications"][0]["relevance"]
assert ranked["objective"]==focused, ranked
assert "determine" not in ranked["query_tokens"], ranked
assert "mars" in ranked["query_tokens"] and "mercury" in ranked["query_tokens"], ranked

live_goal=(
    "Assess whether RFC 9110 obsoletes RFC 7230. "
    "Use authoritative primary technical evidence and preserve provenance."
)
live=discovery.discover(live_goal,limit=6,timeout=12)
assert live.get("query")=="RFC 9110 obsoletes RFC 7230", live
assert live.get("query_strategy")=="DECISION_CLAUSE_FOCUSED__ORCHESTRATION_PROSE_EXCLUDED", live
assert live.get("status")=="CANDIDATES_DISCOVERED", live
assert int(live.get("candidate_count") or 0)>0, live

print("PR510_INDEPENDENT_QUERY_FOCUS_QUALIFIED")
print("focused_query="+focused)
print("live_query="+str(live.get("query")))
print("live_candidate_count="+str(live.get("candidate_count")))
