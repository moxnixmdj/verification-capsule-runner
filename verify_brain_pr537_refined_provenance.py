#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

front=load(FRONT,"pr537_independent_frontend")
failures=[]
cases=[]

def check(label,condition,detail):
    ok=bool(condition)
    cases.append({"label":label,"pass":ok,"detail":detail})
    if not ok:
        failures.append(label)

def decomp(objective):
    return {
        "status":"DECOMPOSED",
        "objective":objective,
        "question_shape":"BOOLEAN_ASSESSMENT",
        "roles":[{"role":"SOURCE_DISCOVERY"}],
    }

class Ranker:
    def __init__(self):
        self.calls=[]
    def rank(self,objective,candidates):
        self.calls.append([dict(c) for c in candidates])
        chosen=0
        for i,c in enumerate(candidates):
            text=" ".join(str(c.get(k) or "") for k in ("title","record_title","snippet"))
            if "target measurement record" in text.lower():
                chosen=i
                break
        return {
            "status":"LEXICAL_RELEVANCE_RANKED",
            "output_verified":True,
            "query_focus":{"query":"target measurement record technical evidence"},
            "top_candidate_original_index":chosen,
            "top_candidate_admission":{"verified":True},
            "ranked_candidates":[],
        }

class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"UNVERIFIED","reason":"NOT_ADMISSION_GATE"}

class Binder:
    @staticmethod
    def bind(*args,**kwargs):
        return {"status":"UNBOUND","reason":"ORACLE_STOPS_AFTER_SOURCE_TRANSITION"}

class Extractor:
    def __init__(self):
        self.calls=[]
    def extract(self,objective,candidate,provenance,relevance,timeout=15):
        self.calls.append({"candidate":dict(candidate),"provenance":dict(provenance)})
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"ORACLE_STOPS_AFTER_SOURCE_TRANSITION"}

def run_case(refined_kind,second_materialize_ok=True):
    objective="Assess a target engineering measurement from authoritative technical evidence."
    ranker=Ranker()
    extractor=Extractor()
    discovery_calls=[]
    materialize_calls=[]

    class Discovery:
        @staticmethod
        def discover(obj,limit=12,timeout=15,query_override=None):
            discovery_calls.append(query_override)
            if query_override is None:
                return {
                    "status":"CANDIDATES_DISCOVERED","objective":obj,
                    "candidates":[
                        {"url":"https://weak.example/live","title":"weak overview","snippet":"general"},
                        {"url":"https://doi.org/10.5555/initial","doi":"10.5555/initial",
                         "title":"Target measurement record initial","snippet":"technical evidence"},
                    ],
                }
            refined=[
                {"url":"https://noise.example/live","title":"noise page","snippet":"general"}
            ]
            if refined_kind=="bibliographic":
                refined.append({
                    "url":"https://doi.org/10.5555/refined","doi":"10.5555/refined",
                    "title":"Target measurement record refined","snippet":"technical evidence",
                })
            else:
                refined.append({
                    "url":"https://target.example/live","title":"Target measurement record live",
                    "snippet":"technical evidence",
                })
            return {
                "status":"CANDIDATES_DISCOVERED","objective":obj,
                "query":query_override,"query_origin":"METADATA_REFINED_OVERRIDE",
                "candidates":refined,
            }

    class Verifier:
        @staticmethod
        def verify(candidate,timeout=15):
            if candidate.get("doi"):
                return {
                    "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                    "candidate_url":candidate["url"],
                    "record_title":candidate["title"],
                    "publisher":"Independent Technical Society",
                }
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":candidate["url"],
                "final_url":candidate["url"],
                "final_host":candidate["url"].split("/")[2],
            }
        @staticmethod
        def materialize(candidate,bibliographic_verification,timeout=15):
            materialize_calls.append(candidate["url"])
            if len(materialize_calls)==1:
                return {
                    "status":"UNVERIFIED",
                    "reason":"DIRECT_SELECTED_MATERIALIZATION_FAILED",
                    "candidate_url":candidate["url"],
                }
            if not second_materialize_ok:
                return {
                    "status":"UNVERIFIED",
                    "reason":"REFINED_SELECTED_MATERIALIZATION_FAILED",
                    "candidate_url":candidate["url"],
                }
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "candidate_url":candidate["url"],
                "final_url":"https://publisher.example/refined",
                "final_host":"publisher.example",
                "selected_only_materialization":True,
            }

    mapping={
        "open_web_source_candidate_discovery":Discovery,
        "source_candidate_provenance_verify":Verifier,
        "objective_relevance_bm25":ranker,
        "objective_evidence_unit_extract":extractor,
        "objective_claim_operand_binding":Binder,
        "source_authority_binding_ror":Authority,
    }
    original=front._load_sibling
    front._load_sibling=lambda name:mapping[name]
    try:
        out=front.run(objective,decomp(objective),limit=8,timeout=2)
    finally:
        front._load_sibling=original
    return out,ranker,extractor,discovery_calls,materialize_calls

# Case A: refined bibliographic winner survives relevance and is materialized selected-only.
out,ranker,extractor,discovery_calls,materialize_calls=run_case("bibliographic",True)
check("bibliographic_refined_ready",out.get("status")=="SOURCE_FRONTEND_READY",out.get("status"))
check("bounded_single_refinement",len(discovery_calls)==2,discovery_calls)
check("refined_relevance_saw_both_verified_classes",
      len(ranker.calls)==2 and len(ranker.calls[1])==2
      and any(c.get("doi")=="10.5555/refined" for c in ranker.calls[1]),
      ranker.calls[1] if len(ranker.calls)>1 else [])
check("selected_bibliographic_materialized_after_relevance",
      materialize_calls==["https://doi.org/10.5555/initial","https://doi.org/10.5555/refined"],
      materialize_calls)
check("refined_bibliographic_origin",
      out.get("selected_source_origin")=="BIBLIOGRAPHIC_METADATA_REFINED_SELECTED_LIVE_MATERIALIZATION",
      out.get("selected_source_origin"))
check("extraction_received_refined_live_provenance",
      len(extractor.calls)==1
      and extractor.calls[0]["candidate"].get("doi")=="10.5555/refined"
      and extractor.calls[0]["provenance"].get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
      and extractor.calls[0]["provenance"].get("final_url")=="https://publisher.example/refined",
      extractor.calls)

# Case B: refined bibliographic materialization failure remains fail-closed.
out2,ranker2,extractor2,discovery2,materialize2=run_case("bibliographic",False)
check("refined_materialization_failure_blocks",
      out2.get("status")=="SELECTED_SOURCE_MATERIALIZATION_BLOCKED",out2.get("status"))
check("refined_failure_no_extraction",extractor2.calls==[],extractor2.calls)
check("refined_failure_still_bounded",len(discovery2)==2,discovery2)

# Case C: refined live winner is not redundantly materialized.
out3,ranker3,extractor3,discovery3,materialize3=run_case("live",True)
check("refined_live_ready",out3.get("status")=="SOURCE_FRONTEND_READY",out3.get("status"))
check("live_winner_not_rematerialized",
      materialize3==["https://doi.org/10.5555/initial"],materialize3)
check("refined_live_origin",
      out3.get("selected_source_origin")=="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL",
      out3.get("selected_source_origin"))
check("refined_live_extraction",
      len(extractor3.calls)==1
      and extractor3.calls[0]["candidate"].get("url")=="https://target.example/live",
      extractor3.calls)

report={
    "schema":"BRAIN_PR537_REFINED_PROVENANCE_INDEPENDENT_QUALIFICATION_V1",
    "status":"PASS" if not failures else "FAIL",
    "brain_pr":537,
    "brain_candidate_head":"2c4f2d9bc02d07dcd61d7fc6d01f38c679941813",
    "failures":failures,
    "cases":cases,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "materials_task_c_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
}
(ROOT/"pr537-independent-refined-provenance-report.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not failures else 1)
