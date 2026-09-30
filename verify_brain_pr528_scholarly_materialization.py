#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr528_ind_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

front=load("open_research_source_frontend")
prov=load("source_candidate_provenance_verify")
ranker=load("objective_relevance_bm25")
extractor=load("objective_evidence_unit_extract")

fail=[]
cases=[]
def check(label,cond,detail=None):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond:
        fail.append(label)

# 1) Real ranker: weak generic metadata must not be admitted; strong subject metadata must.
objective=(
    "Assess whether sodium ion battery cycle life exceeds 2000 cycles at 25 C. "
    "Use authoritative experimental evidence and preserve provenance."
)
weak=[{
    "url":"https://generic.example/2026",
    "title":"Battery news in 2026",
    "snippet":"General battery industry news.",
}]
weak_rank=ranker.rank(objective,weak)
check(
    "weak_subject_coverage_rejected",
    weak_rank.get("status")=="LEXICAL_RELEVANCE_RANKED"
    and (weak_rank.get("top_candidate_admission") or {}).get("verified") is False,
    weak_rank,
)
strong=[{
    "url":"https://doi.org/10.5555/sodium-cycle",
    "doi":"10.5555/sodium-cycle",
    "title":"Sodium ion battery cycle life",
    "record_title":"Sodium ion battery cycle life exceeds 2000 cycles at 25 C",
}]
strong_rank=ranker.rank(objective,strong)
check(
    "strong_subject_coverage_admitted",
    strong_rank.get("status")=="LEXICAL_RELEVANCE_RANKED"
    and (strong_rank.get("top_candidate_admission") or {}).get("verified") is True,
    strong_rank,
)

# 2) Receipt binding: wrong bibliographic identity must fail before any fetch.
fetch_calls=[]
def forbidden_fetch(*args,**kwargs):
    fetch_calls.append(args)
    raise AssertionError("FETCH_MUST_NOT_RUN_ON_IDENTITY_MISMATCH")
identity=prov.materialize_retrieval(
    {"url":"https://doi.org/10.5555/right","doi":"10.5555/right"},
    {
        "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
        "candidate_url":"https://doi.org/10.5555/wrong",
        "doi":"10.5555/wrong",
        "record_title":"Wrong record",
    },
    timeout=2,
    fetch=forbidden_fetch,
)
check(
    "bibliographic_identity_mismatch_fails_pre_fetch",
    identity.get("status")=="UNVERIFIED"
    and identity.get("reason")=="BIBLIOGRAPHIC_CANDIDATE_IDENTITY_MISMATCH"
    and not fetch_calls,
    identity,
)

# 3) Materialized DOI may redirect, but extraction must remain bound to DOI selection
# and freshly refetch the exact materialized final URL.
candidate={
    "url":"https://doi.org/10.5555/sodium-cycle",
    "doi":"10.5555/sodium-cycle",
    "title":"Sodium ion battery cycle life",
}
bib={
    "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
    "candidate_url":candidate["url"],
    "doi":candidate["doi"],
    "record_title":"Sodium ion battery cycle life exceeds 2000 cycles at 25 C",
    "verification_method":"CROSSREF_DOI_RECORD",
}
def materialize_fetch(url,timeout,accept):
    return (
        b"<html><title>Sodium battery study</title></html>",
        "text/html",
        200,
        "https://publisher.example/sodium-cycle",
    )
live=prov.materialize_retrieval(candidate,bib,timeout=2,fetch=materialize_fetch)
check(
    "doi_materialization_preserves_bibliographic_identity",
    live.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
    and live.get("selected_only_materialization") is True
    and live.get("bibliographic_identity_preserved") is True
    and live.get("final_url")=="https://publisher.example/sodium-cycle"
    and live.get("authority_status")=="RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",
    live,
)
relevance=ranker.rank(objective,[{**candidate,"record_title":bib["record_title"]}])
def evidence_fetch(url,timeout):
    check("extractor_fetches_materialized_final_url",url=="https://publisher.example/sodium-cycle",url)
    return (
        b"<html><body><p>Sodium ion battery cycle life reached 2200 cycles at 25 C in the reported experiment.</p></body></html>",
        "https://publisher.example/sodium-cycle",
        "text/html",
        200,
    )
extracted=extractor.extract(
    objective,candidate,live,relevance,timeout=2,fetch=evidence_fetch
)
check(
    "materialized_doi_extracts_only_after_live_provenance",
    extracted.get("status")=="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
    and int(extracted.get("evidence_unit_count") or 0)>=1,
    extracted,
)

# 4) Frontend fallback: if selected DOI cannot materialize directly, only verified
# bibliographic metadata may refine discovery. The original objective still ranks
# the refined live candidates.
fallback_objective=(
    "Assess whether lithium iron phosphate battery cycle life exceeds 3000 cycles at 25 C. "
    "Use authoritative experimental evidence and preserve provenance."
)
weak_live={
    "url":"https://generic.example/battery",
    "host":"generic.example",
    "title":"Battery industry overview",
    "snippet":"General battery information.",
}
bib_candidate={
    "url":"https://doi.org/10.7777/lfp-cycle",
    "host":"doi.org",
    "doi":"10.7777/lfp-cycle",
    "title":"Lithium iron phosphate battery cycle life",
}
refined_live={
    "url":"https://publisher.example/lfp-cycle",
    "host":"publisher.example",
    "title":"Lithium iron phosphate battery cycle life exceeds 3000 cycles at 25 C",
    "snippet":"Experimental cycle-life measurements for LFP cells.",
}
class Discovery:
    overrides=[]
    @staticmethod
    def discover(obj,limit=12,timeout=15,query_override=None):
        if query_override is None:
            return {
                "status":"CANDIDATES_DISCOVERED",
                "objective":obj,
                "query":"lfp battery cycle life 3000 cycles 25 c",
                "candidates":[weak_live,bib_candidate],
            }
        Discovery.overrides.append(query_override)
        return {
            "status":"CANDIDATES_DISCOVERED",
            "objective":obj,
            "query":query_override,
            "query_origin":"METADATA_REFINED_OVERRIDE",
            "candidates":[refined_live],
        }
class Verifier:
    @staticmethod
    def verify(c,timeout=15):
        if c.get("doi"):
            return {
                "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
                "candidate_url":c["url"],
                "doi":c["doi"],
                "record_title":"Lithium iron phosphate battery cycle life exceeds 3000 cycles at 25 C",
                "verification_method":"CROSSREF_DOI_RECORD",
            }
        return {
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":c["url"],
            "final_url":c["url"],
            "final_host":c["host"],
        }
    @staticmethod
    def materialize_retrieval(c,bibliographic_verification,timeout=15,fetch=None):
        return {
            "status":"UNVERIFIED",
            "reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED",
            "candidate_url":c["url"],
            "bibliographic_provenance_status":"VERIFIED",
        }
seen_extract=[]
class Extractor:
    @staticmethod
    def extract(obj,candidate,provenance,relevance,timeout=15):
        seen_extract.append({
            "candidate":dict(candidate),
            "provenance":dict(provenance),
            "relevance":dict(relevance),
        })
        return {
            "status":"EVIDENCE_EXTRACTION_BLOCKED",
            "reason":"INDEPENDENT_ORACLE_STOPS_AFTER_SOURCE_TRANSITION",
        }
class Binder:
    @staticmethod
    def bind(*args,**kwargs):
        raise AssertionError("BINDER_MUST_NOT_RUN")
class Authority:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"AUTHORITY_UNRESOLVED","reason":"ORACLE"}
mapping={
    "open_web_source_candidate_discovery":Discovery,
    "source_candidate_provenance_verify":Verifier,
    "objective_relevance_bm25":ranker,
    "objective_evidence_unit_extract":Extractor,
    "objective_claim_operand_binding":Binder,
    "source_authority_binding_ror":Authority,
}
old_loader=front._load_sibling
front._load_sibling=lambda name:mapping[name]
try:
    decomp={
        "status":"DECOMPOSED",
        "objective":fallback_objective,
        "question_shape":"BOOLEAN_ASSESSMENT",
        "roles":[{"role":"SOURCE_DISCOVERY"}],
    }
    fallback=front.run(fallback_objective,decomp,limit=8,timeout=2)
finally:
    front._load_sibling=old_loader
check(
    "metadata_refinement_uses_verified_record_title",
    len(Discovery.overrides)==1
    and "lithium iron phosphate battery cycle life exceeds 3000 cycles at 25 c"
        in Discovery.overrides[0].lower(),
    Discovery.overrides,
)
check(
    "metadata_refinement_selects_live_source_without_replaying_parent",
    fallback.get("status")=="SOURCE_FRONTEND_READY"
    and len(seen_extract)==1
    and seen_extract[0]["candidate"]["url"]==refined_live["url"]
    and seen_extract[0]["provenance"]["status"]=="RETRIEVAL_PROVENANCE_VERIFIED",
    {"fallback":fallback,"seen_extract":seen_extract},
)

report={
    "schema":"BRAIN_PR528_SCHOLARLY_MATERIALIZATION_INDEPENDENT_QUALIFICATION_V1",
    "status":"PASS" if not fail else "FAIL",
    "brain_pr":528,
    "failures":fail,
    "cases":cases,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "seismology_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
}
(ROOT/"pr528-independent-scholarly-materialization-report.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
