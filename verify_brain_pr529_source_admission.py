#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"
def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr529_ind_"+name,p)
    if spec is None or spec.loader is None: raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m
front=load("open_research_source_frontend")
prov=load("source_candidate_provenance_verify")
ranker=load("objective_relevance_bm25")
fail=[]; cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)
def decomp(obj):
    return {"status":"DECOMPOSED","objective":obj,"question_shape":"BOOLEAN_ASSESSMENT","roles":[{"role":"SOURCE_DISCOVERY"}]}

# Identity binding must precede selected materialization.
m=prov.materialize(
 {"url":"https://doi.org/10.7777/a","doi":"10.7777/a"},
 {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","candidate_url":"https://doi.org/10.7777/b","doi":"10.7777/b"},
 fetch=lambda *a,**k: (_ for _ in ()).throw(AssertionError("FETCH_MUST_NOT_RUN"))
)
check("identity_mismatch_fail_closed",m.get("reason")=="BIBLIOGRAPHIC_CANDIDATE_IDENTITY_MISMATCH",m)

# Relevance admission must reject a weak positive hit, not merely require score > 0.
weak=ranker.rank(
 "Assess whether lithium ion battery thermal runaway onset temperature exceeds 150 C.",
 [{"url":"https://weak.example","title":"2026 overview","snippet":"battery overview"}]
)
check("weak_positive_not_admitted",
      weak.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and (weak.get("top_candidate_admission") or {}).get("verified") is False,weak)

objective=(
 "Assess whether lithium ion battery thermal runaway onset temperature exceeds 150 C. "
 "Use technical evidence and independently verify the result."
)
weakc={"url":"https://weak.example/page","title":"2026 battery overview","snippet":"general battery news"}
schol={"url":"https://doi.org/10.7777/thermal","doi":"10.7777/thermal",
       "title":"Lithium ion battery thermal runaway onset temperature 150 C measurements",
       "snippet":"thermal runaway onset temperature measured across cells"}
calls={"discover":[],"materialize":[],"extract":[]}

class Discovery:
    @staticmethod
    def discover(obj,limit=12,timeout=15,query_override=None):
        calls["discover"].append(query_override)
        if query_override is None:
            return {"status":"CANDIDATES_DISCOVERED","objective":obj,"candidates":[weakc,schol]}
        return {"status":"CANDIDATES_DISCOVERED","objective":obj,"query":query_override,
                "query_origin":"METADATA_REFINED_OVERRIDE","candidates":[{
                    "url":"https://lab.example/thermal-record","title":"Lithium ion battery thermal runaway onset temperature 150 C laboratory record",
                    "snippet":"measured thermal runaway onset temperature 165 C","source_class":"OPEN_WEB_SEARCH_CANDIDATE"
                }]}
class Verifier:
    @staticmethod
    def verify(candidate,timeout=15):
        if candidate.get("doi"):
            return {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","candidate_url":candidate["url"],
                    "doi":candidate["doi"],"record_title":candidate["title"],
                    "publisher":"Battery Research Society","verification_method":"CROSSREF_DOI_RECORD"}
        host=candidate["url"].split("/")[2]
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],
                "final_url":candidate["url"],"final_host":host}
    @staticmethod
    def materialize(candidate,bib,timeout=15,fetch=None):
        calls["materialize"].append(candidate["url"])
        return {"status":"UNVERIFIED","reason":"TEST_DIRECT_MATERIALIZATION_BLOCKED","candidate_url":candidate["url"]}
class Extractor:
    @staticmethod
    def extract(obj,candidate,provenance,relevance,timeout=15):
        calls["extract"].append((candidate["url"],provenance.get("final_url")))
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"ORACLE_STOPS_AFTER_REFINED_TRANSITION"}
class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15): return {"status":"UNVERIFIED","reason":"ORACLE"}
class Binder:
    @staticmethod
    def bind(*a,**k): raise AssertionError("BINDER_MUST_NOT_RUN")

orig=front._load_sibling
front._load_sibling=lambda name:{
 "open_web_source_candidate_discovery":Discovery,
 "source_candidate_provenance_verify":Verifier,
 "objective_relevance_bm25":ranker,
 "objective_evidence_unit_extract":Extractor,
 "objective_claim_operand_binding":Binder,
 "source_authority_binding_ror":Authority,
}[name]
try:
    out=front.run(objective,decomp(objective),limit=8,timeout=2)
finally:
    front._load_sibling=orig
check("bibliographic_candidate_survives_initial_relevance",
      (out.get("selected_source_materialization") or {}).get("reason")=="TEST_DIRECT_MATERIALIZATION_BLOCKED",out)
check("selected_only_materialization",calls["materialize"]==[schol["url"]],calls)
check("exactly_one_metadata_refinement",
      len(calls["discover"])==2 and calls["discover"][0] is None and calls["discover"][1] is not None,calls)
check("refined_query_is_metadata_anchored",
      "Lithium ion battery thermal runaway onset temperature 150 C measurements" in str(calls["discover"][1]),calls)
check("refined_live_source_reaches_extraction",
      calls["extract"]==[("https://lab.example/thermal-record","https://lab.example/thermal-record")],calls)
check("refined_origin_recorded",
      out.get("selected_source_origin")=="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL",out)

# Failed refinement must stop, never fall back to weak initial page.
touch=[]
class DiscoveryFail(Discovery):
    @staticmethod
    def discover(obj,limit=12,timeout=15,query_override=None):
        if query_override is None:
            return {"status":"CANDIDATES_DISCOVERED","objective":obj,"candidates":[weakc,schol]}
        return {"status":"DISCOVERY_UNAVAILABLE","objective":obj,"candidates":[]}
front._load_sibling=lambda name:{
 "open_web_source_candidate_discovery":DiscoveryFail,
 "source_candidate_provenance_verify":Verifier,
 "objective_relevance_bm25":ranker,
 "objective_evidence_unit_extract":type("X",(),{"extract":staticmethod(lambda *a,**k: touch.append("extract"))}),
 "objective_claim_operand_binding":Binder,
 "source_authority_binding_ror":Authority,
}[name]
try:
    blocked=front.run(objective,decomp(objective),limit=8,timeout=2)
finally:
    front._load_sibling=orig
check("failed_refinement_fails_closed",
      blocked.get("status")=="SELECTED_SOURCE_MATERIALIZATION_BLOCKED" and touch==[],blocked)

report={
 "schema":"BRAIN_PR529_SOURCE_ADMISSION_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS" if not fail else "FAIL",
 "brain_pr":529,
 "brain_candidate_head":"4df38e5aa55cfd86a1fda6fbe11666ab6221da2c",
 "failures":fail,"cases":cases,
 "parent_task_execution":False,"parent_task_replay":False,
 "model_dependency_count":0,"incremental_spend_usd":0
}
(ROOT/"pr529-independent-source-admission-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
