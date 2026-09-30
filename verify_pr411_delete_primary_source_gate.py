#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
spec=importlib.util.spec_from_file_location("pr411_frontend",P)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)

class Discovery:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {
          "status":"CANDIDATES_DISCOVERED",
          "candidates":[
            {"url":"https://verified.example/evidence","title":"relevant candidate"},
            {"url":"https://unverified.example/noise","title":"noise"},
          ],
          "model_dependency_count":0,"incremental_spend_usd":0,
        }
class Provenance:
    @staticmethod
    def verify(candidate,timeout=15):
        if "verified.example" in candidate["url"]:
            return {
              "status":"RETRIEVAL_PROVENANCE_VERIFIED",
              "final_url":"https://verified.example/evidence",
              "final_host":"verified.example",
            }
        return {"status":"UNVERIFIED"}
class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=20):
        assert candidate.get("final_host")=="verified.example"
        return {
          "status":"AUTHORITY_IDENTITY_VERIFIED",
          "authority_status":"VERIFIED",
          "matched_domain":"verified.example",
          "primary_source_status":"UNVERIFIED",
          "relevance_status":"UNVERIFIED",
          "evidence_sufficiency_status":"UNVERIFIED",
          "model_dependency_count":0,
          "incremental_spend_usd":0,
        }

orig=m._load_sibling
def fake(name):
    if name=="open_web_source_candidate_discovery": return Discovery
    if name=="source_candidate_provenance_verify": return Provenance
    if name=="source_authority_binding_ror": return Authority
    return orig(name)
m._load_sibling=fake

goal="Assess whether a documented technical claim is supported by authoritative evidence"
decomposition={
 "status":"DECOMPOSED",
 "objective":goal,
 "question_shape":"ASSESSMENT",
 "roles":[{"role":"SOURCE_DISCOVERY"}],
}
out=m.run(goal,decomposition,limit=8,timeout=5)
checks={
 "frontend_ready":out.get("status")=="SOURCE_FRONTEND_READY",
 "authority_identity_present":out.get("authority_identity_verified_candidate_count")==1,
 "primary_source_not_required":out.get("primary_source_gate_required") is False,
 "primary_source_still_unverified":out.get("primary_source_verified_candidate_count")==0 and out.get("primary_source_claims_made") is False,
 "relevance_still_unverified":out.get("relevance_verified_candidate_count")==0 and out.get("relevance_claims_made") is False,
 "next_gap_relevance_only":out.get("next_required_capability")=="MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_V1",
 "role_blocks_on_relevance_only":out.get("role_progress",{}).get("EVIDENCE_ACQUISITION")=="BLOCKED_ON_OBJECTIVE_RELEVANCE_VERIFICATION",
 "model_free":out.get("model_dependency_count")==0,
 "zero_spend":out.get("incremental_spend_usd")==0,
}
report={
 "schema":"PROJECT_BRAIN_PR411_DELETE_PRIMARY_SOURCE_GATE_QUALIFICATION_V1",
 "checks":checks,
 "output":out,
 "qualified":all(checks.values()),
 "model_dependency_count":0,
 "incremental_spend_usd":0,
}
(ROOT/"pr411-delete-primary-source-gate-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["qualified"] else 1)
