#!/usr/bin/env python3
"""Compose qualified source discovery gates for broad open research.

This module does not answer research questions or claim evidence sufficiency.
It advances candidates through:
  discovery -> live retrieval provenance -> authority identity ->
  first-party technical primary/relevance verification.

Only candidates that pass every gate are exposed as ready for evidence
acquisition.
"""
from __future__ import annotations

import importlib.util
import pathlib

SCHEMA="PROJECT_BRAIN_QUALIFIED_SOURCE_FRONTEND_V1"


def _load_sibling(name):
    path=pathlib.Path(__file__).resolve().with_name(name+".py")
    spec=importlib.util.spec_from_file_location("project_brain_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canon(value):
    return " ".join(str(value or "").strip().split())


def _base(objective,decomposition):
    return {
        "schema":SCHEMA,
        "objective":objective,
        "question_shape":decomposition.get("question_shape"),
        "decomposition":decomposition,
        "qualified_sources":[],
        "qualified_source_count":0,
        "evidence_sufficiency_verification":"NOT_PERFORMED",
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }


def run(
    objective,
    decomposition,
    limit=12,
    timeout=15,
    discovery_fn=None,
    provenance_fn=None,
    authority_fn=None,
    primary_relevance_fn=None,
):
    objective=_canon(objective)
    if not objective:
        raise ValueError("OBJECTIVE_REQUIRED")
    if not isinstance(decomposition,dict) or decomposition.get("status")!="DECOMPOSED":
        raise ValueError("QUALIFIED_DECOMPOSITION_REQUIRED")
    if _canon(decomposition.get("objective"))!=objective:
        raise ValueError("DECOMPOSITION_OBJECTIVE_MISMATCH")
    roles=decomposition.get("roles")
    if not isinstance(roles,list) or not any(
        isinstance(x,dict) and x.get("role")=="SOURCE_DISCOVERY" for x in roles
    ):
        raise ValueError("SOURCE_DISCOVERY_ROLE_REQUIRED")

    if discovery_fn is None:
        discovery_fn=_load_sibling("open_web_source_candidate_discovery").discover
    if provenance_fn is None:
        provenance_fn=_load_sibling("source_candidate_provenance_verify").verify
    if authority_fn is None:
        authority_fn=_load_sibling("source_authority_binding_wikidata").bind_candidate
    if primary_relevance_fn is None:
        primary_relevance_fn=_load_sibling("official_primary_relevance_verify").verify

    discovered=discovery_fn(objective,limit=limit,timeout=timeout)
    out=_base(objective,decomposition)
    out["discovery"]=discovered
    out["candidate_gate_results"]=[]

    if not isinstance(discovered,dict) or discovered.get("status")!="CANDIDATES_DISCOVERED":
        out.update({
            "status":"SOURCE_DISCOVERY_BLOCKED",
            "next_required_capability":"MODEL_INDEPENDENT_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
            "role_progress":{
                "SOURCE_DISCOVERY":"BLOCKED",
                "EVIDENCE_ACQUISITION":"NOT_STARTED",
            },
        })
        return out

    live_count=0
    authority_count=0
    primary_relevance_count=0

    for candidate in discovered.get("candidates") or []:
        record={"candidate":candidate}
        try:
            provenance=provenance_fn(candidate,timeout=timeout)
        except Exception as exc:
            provenance={"status":"UNVERIFIED","reason":type(exc).__name__+":"+str(exc)[:300]}
        record["provenance"]=provenance

        if not isinstance(provenance,dict) or provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
            record["gate_status"]="LIVE_RETRIEVAL_REQUIRED"
            out["candidate_gate_results"].append(record)
            continue
        live_count+=1

        try:
            authority=authority_fn(candidate,timeout=timeout)
        except Exception as exc:
            authority={
                "status":"AUTHORITY_UNRESOLVED",
                "authority_status":"UNVERIFIED",
                "reason":type(exc).__name__+":"+str(exc)[:300],
            }
        record["authority"]=authority
        if (
            not isinstance(authority,dict)
            or authority.get("status")!="AUTHORITY_IDENTITY_VERIFIED"
            or authority.get("authority_status")!="VERIFIED"
        ):
            record["gate_status"]="AUTHORITY_UNRESOLVED"
            out["candidate_gate_results"].append(record)
            continue
        authority_count+=1

        try:
            primary=primary_relevance_fn(
                objective,candidate,provenance,authority,timeout=timeout
            )
        except Exception as exc:
            primary={
                "status":"UNVERIFIED",
                "primary_source_status":"UNVERIFIED",
                "relevance_status":"UNVERIFIED",
                "evidence_sufficiency_status":"UNVERIFIED",
                "reason":type(exc).__name__+":"+str(exc)[:300],
            }
        record["primary_relevance"]=primary
        if not isinstance(primary,dict) or primary.get("status")!="PRIMARY_RELEVANCE_VERIFIED":
            record["gate_status"]="PRIMARY_OR_RELEVANCE_UNRESOLVED"
            out["candidate_gate_results"].append(record)
            continue

        primary_relevance_count+=1
        record["gate_status"]="QUALIFIED_SOURCE"
        out["candidate_gate_results"].append(record)
        out["qualified_sources"].append(record)

    out["live_retrieval_verified_candidate_count"]=live_count
    out["authority_verified_candidate_count"]=authority_count
    out["primary_relevance_verified_candidate_count"]=primary_relevance_count
    out["qualified_source_count"]=len(out["qualified_sources"])

    if out["qualified_sources"]:
        out.update({
            "status":"QUALIFIED_SOURCE_AVAILABLE",
            "next_required_capability":"MODEL_INDEPENDENT_EVIDENCE_ACQUISITION_FROM_QUALIFIED_SOURCE",
            "role_progress":{
                "SOURCE_DISCOVERY":"QUALIFIED_SOURCE_AVAILABLE",
                "EVIDENCE_ACQUISITION":"READY_TO_ACQUIRE_FROM_QUALIFIED_SOURCE",
                "EVIDENCE_EXTRACTION":"NOT_STARTED",
                "RELATION_EVALUATION":"NOT_STARTED",
                "DECISION_SYNTHESIS_AND_VERIFICATION":"NOT_STARTED",
            },
        })
        return out

    if live_count==0:
        status="SOURCE_LIVE_RETRIEVAL_BLOCKED"
        next_cap="MODEL_INDEPENDENT_LIVE_SOURCE_RETRIEVAL_PROVENANCE"
    elif authority_count==0:
        status="SOURCE_AUTHORITY_BLOCKED"
        next_cap="MODEL_INDEPENDENT_SOURCE_AUTHORITY_BINDING"
    else:
        status="SOURCE_PRIMARY_RELEVANCE_BLOCKED"
        next_cap="MODEL_INDEPENDENT_OFFICIAL_PRIMARY_RELEVANCE_VERIFICATION"

    out.update({
        "status":status,
        "next_required_capability":next_cap,
        "role_progress":{
            "SOURCE_DISCOVERY":"CANDIDATES_AVAILABLE",
            "EVIDENCE_ACQUISITION":"BLOCKED",
        },
    })
    return out
