#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr528_ind_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

front=load("open_research_source_frontend")
prov=load("source_candidate_provenance_verify")
relevance=load("objective_relevance_bm25")

fail=[]
cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond:
        fail.append(label)

# 1) Direct identity-bound materialization: mismatch must fail before fetch.
mismatch=prov.materialize(
    {"url":"https://doi.org/10.5555/alpha","doi":"10.5555/alpha"},
    {
      "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
      "candidate_url":"https://doi.org/10.5555/beta",
      "doi":"10.5555/beta",
    },
    fetch=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("FETCH_MUST_NOT_RUN")),
)
check("identity_mismatch_fails_closed",
      mismatch.get("status")=="UNVERIFIED" and mismatch.get("reason")=="BIBLIOGRAPHIC_CANDIDATE_IDENTITY_MISMATCH",
      mismatch)

# 2) Direct materialization success remains a provenance transition, not authority.
def fake_fetch(url,timeout,accept):
    return (
      b"<html><title>Battery Study</title><body>thermal runaway data</body></html>",
      "text/html",
      200,
      "https://publisher.example/battery-study",
    )
mat=prov.materialize(
    {"url":"https://doi.org/10.5555/battery","doi":"10.5555/battery"},
    {
      "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
      "candidate_url":"https://doi.org/10.5555/battery",
      "doi":"10.5555/battery",
      "record_title":"Lithium ion battery thermal runaway onset temperature measurements",
      "verification_method":"CROSSREF_DOI_RECORD",
    },
    timeout=4,
    fetch=fake_fetch,
)
check("materialization_success",mat.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED",mat)
check("materialization_selected_only",mat.get("selected_only_materialization") is True,mat)
check("materialization_no_authority_upgrade",
      mat.get("authority_status")=="RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED"
      and mat.get("primary_source_status")=="UNVERIFIED",mat)

def decomp(obj):
    return {"status":"DECOMPOSED","objective":obj,"question_shape":"BOOLEAN_ASSESSMENT","roles":[{"role":"SOURCE_DISCOVERY"}]}

# Shared integration fakes use actual candidate ranking implementation.
class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"INDEPENDENT_ORACLE"}

class Binder:
    @staticmethod
    def bind(*args,**kwargs):
        raise AssertionError("BINDER_MUST_NOT_RUN_WHEN_EXTRACTION_IS_BLOCKED")

# 3) Cross-domain battery case: strong scholarly metadata must beat weak live page,
# materialize only the scholarly winner, then pass live provenance to extraction.
objective=(
  "Assess whether lithium ion battery thermal runaway onset temperature exceeds 150 C. "
  "Use authoritative technical evidence and independently verify the result."
)
weak={"url":"https://weak.example/2026","title":"2026 technology overview","snippet":"general technology overview"}
scholarly={
  "url":"https://doi.org/10.5555/thermal","doi":"10.5555/thermal",
  "title":"Lithium ion battery thermal runaway onset temperature measurements 150 C",
  "snippet":"battery thermal runaway onset temperature measurement study",
}
materialized=[]
extracted=[]
class DiscoveryA:
    @staticmethod
    def discover(obj,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","objective":obj,"candidates":[weak,scholarly]}
class VerifierA:
    @staticmethod
    def verify(candidate,timeout=15):
        if candidate.get("doi"):
            return {
              "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
              "candidate_url":candidate["url"],
              "doi":candidate["doi"],
              "record_title":"Lithium ion battery thermal runaway onset temperature measurements 150 C",
              "publisher":"Independent Battery Society",
              "verification_method":"CROSSREF_DOI_RECORD",
            }
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":"weak.example",
        }
    @staticmethod
    def materialize(candidate,bibliographic_verification,timeout=15):
        materialized.append(candidate["url"])
        check("materializer_receives_verified_bibliographic_identity",
              bibliographic_verification.get("status")=="BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
              bibliographic_verification)
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "verification_method":"SELECTED_BIBLIOGRAPHIC_CANDIDATE_LIVE_HTTP_MATERIALIZATION",
          "candidate_url":candidate["url"],
          "final_url":"https://publisher.example/thermal",
          "final_host":"publisher.example",
          "selected_only_materialization":True,
          "authority_status":"RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
          "primary_source_status":"UNVERIFIED",
        }
class ExtractorA:
    @staticmethod
    def extract(obj,candidate,provenance,rel,timeout=15):
        extracted.append({"candidate":candidate,"provenance":provenance})
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"ORACLE_STOPS_AFTER_TRANSITION"}

orig=front._load_sibling
def fakeA(name):
    return {
      "open_web_source_candidate_discovery":DiscoveryA,
      "source_candidate_provenance_verify":VerifierA,
      "objective_relevance_bm25":relevance,
      "objective_evidence_unit_extract":ExtractorA,
      "objective_claim_operand_binding":Binder,
      "source_authority_binding_ror":Authority,
    }[name]
front._load_sibling=fakeA
try:
    outA=front.run(objective,decomp(objective),limit=8,timeout=2)
finally:
    front._load_sibling=orig
selected=((outA.get("objective_relevance_verifications") or [{}])[0].get("candidate") or {})
check("scholarly_candidate_wins_relevance",selected.get("url")==scholarly["url"],outA)
check("only_selected_scholarly_materialized",materialized==[scholarly["url"]],materialized)
check("extraction_receives_live_materialized_provenance",
      len(extracted)==1
      and extracted[0]["provenance"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
      and extracted[0]["provenance"].get("final_url")=="https://publisher.example/thermal",
      extracted)

# 4) Weak-only relevance must not proceed to extraction/materialization.
weak_only={"url":"https://weak.example/overview","title":"2026 overview","snippet":"general overview"}
touch=[]
class DiscoveryB:
    @staticmethod
    def discover(obj,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","objective":obj,"candidates":[weak_only]}
class VerifierB:
    @staticmethod
    def verify(candidate,timeout=15):
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":"weak.example"}
    @staticmethod
    def materialize(*args,**kwargs):
        touch.append("materialize")
        raise AssertionError("WEAK_RELEVANCE_MUST_NOT_MATERIALIZE")
class ExtractorB:
    @staticmethod
    def extract(*args,**kwargs):
        touch.append("extract")
        raise AssertionError("WEAK_RELEVANCE_MUST_NOT_EXTRACT")
def fakeB(name):
    return {
      "open_web_source_candidate_discovery":DiscoveryB,
      "source_candidate_provenance_verify":VerifierB,
      "objective_relevance_bm25":relevance,
      "objective_evidence_unit_extract":ExtractorB,
      "objective_claim_operand_binding":Binder,
      "source_authority_binding_ror":Authority,
    }[name]
front._load_sibling=fakeB
try:
    outB=front.run(objective,decomp(objective),limit=8,timeout=2)
finally:
    front._load_sibling=orig
check("weak_relevance_not_admitted",outB.get("relevance_verified_candidate_count")==0,outB)
check("weak_relevance_stops_before_actions",touch==[],touch)

report={
 "schema":"BRAIN_PR528_SCHOLARLY_ADMISSION_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS" if not fail else "FAIL",
 "brain_pr":528,
 "brain_candidate_head":"6d4064312705eaa11ce5817287934e6c5d87d5f4",
 "failures":fail,
 "cases":cases,
 "parent_task_execution":False,
 "parent_task_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr528-independent-scholarly-admission-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
