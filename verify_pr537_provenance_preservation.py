#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,types

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
spec=importlib.util.spec_from_file_location("pr537_frontend_oracle",P)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Discovery:
    def __init__(self): self.calls=[]
    def discover(self,objective,limit=12,timeout=15,query_override=None):
        self.calls.append(query_override)
        if query_override is None:
            return {"status":"CANDIDATES_DISCOVERED","candidates":[
                {"url":"https://doi.org/10.1111/initial","host":"doi.org","title":"Initial bibliography"}
            ]}
        return {"status":"CANDIDATES_DISCOVERED","candidates":[
            {"url":"https://live.example/a","host":"live.example","title":"Weak live record"},
            {"url":"https://doi.org/10.2222/refined","host":"doi.org","title":"Strong refined measurement study"}
        ]}

class Verifier:
    def __init__(self): self.materialize_calls=[]
    def verify(self,candidate,timeout=15):
        u=candidate["url"]
        if "doi.org" in u:
            return {
              "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
              "record_title":candidate["title"],"publisher":"Publisher",
              "doi":u.rsplit("/",1)[-1]
            }
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "final_url":u,"final_host":candidate["host"]
        }
    def materialize(self,candidate,verification,timeout=15,fetch=None):
        self.materialize_calls.append(candidate["url"])
        if candidate["url"].endswith("/initial"):
            return {"status":"LIVE_MATERIALIZATION_FAILED","reason":"INITIAL_FAIL"}
        return {
          "status":"RETRIEVAL_PROVENANCE_VERIFIED",
          "final_url":"https://publisher.example/refined",
          "final_host":"publisher.example",
          "bibliographic_identity_preserved":True,
          "selected_only_materialization":True
        }

class Ranker:
    def rank(self,objective,candidates):
        # Initial set has one bibliographic candidate. Refined set deliberately
        # chooses the bibliographic candidate at index 1.
        idx=0 if len(candidates)==1 else 1
        return {
          "status":"LEXICAL_RELEVANCE_RANKED","output_verified":True,
          "top_candidate_original_index":idx,
          "top_candidate_admission":{"verified":True},
          "query_focus":{"query":"thermal conductivity annealed alloy comparative"}
        }

class Extractor:
    def __init__(self): self.calls=[]
    def extract(self,objective,candidate,provenance,relevance,timeout=15):
        self.calls.append((dict(candidate),dict(provenance)))
        return {"status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","evidence_unit_count":1}

class Binder:
    def bind(self,objective,extraction,evaluate_relation=True):
        return {
          "status":"CLAIM_SPEC_BOUND",
          "relation_result":{"status":"EXACT_TEXT_SUPPORT_VERIFIED","output_verified":True}
        }

class Authority:
    def bind_candidate(self,candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"OPTIONAL"}

discovery=Discovery(); verifier=Verifier(); ranker=Ranker(); extractor=Extractor()
mods={
 "open_web_source_candidate_discovery":discovery,
 "source_candidate_provenance_verify":verifier,
 "objective_relevance_bm25":ranker,
 "objective_evidence_unit_extract":extractor,
 "objective_claim_operand_binding":Binder(),
 "source_authority_binding_ror":Authority(),
}
mod._load_sibling=lambda name: mods[name]

objective=(
 "Assess whether the room-temperature thermal conductivity of one annealed alloy "
 "is greater than another annealed alloy. Use authoritative technical evidence "
 "and independently verify the consequential result."
)
decomp={"status":"DECOMPOSED","objective":objective,"question_shape":"BOOLEAN_ASSESSMENT","roles":[{"role":"SOURCE_DISCOVERY"}]}
out=mod.run(objective,decomp,limit=12,timeout=1)

assert verifier.materialize_calls==[
 "https://doi.org/10.1111/initial",
 "https://doi.org/10.2222/refined",
], verifier.materialize_calls
assert out["selected_source_origin"]=="BIBLIOGRAPHIC_METADATA_REFINED_SELECTED_LIVE_MATERIALIZATION", out
assert len(extractor.calls)==1, extractor.calls
cand,prov=extractor.calls[0]
assert cand["url"]=="https://doi.org/10.2222/refined", cand
assert prov["status"]=="RETRIEVAL_PROVENANCE_VERIFIED", prov
assert prov["final_url"]=="https://publisher.example/refined", prov
assert (out["metadata_anchored_refinement"] or {})["selected"] is True
assert (out["metadata_anchored_refinement"] or {})["selected_materialization"]["status"]=="RETRIEVAL_PROVENANCE_VERIFIED"

report={
 "schema":"PROJECT_BRAIN_PR537_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":537,
 "frontend_blob":"96c63f6586df27a2bf2f508f1f83215676cdd4c8",
 "refined_provenance_classes_preserved":True,
 "selected_bibliographic_winner_materialized_only_after_relevance":True,
 "parent_task_execution":False,
 "materials_task_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr537-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
