#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"pr444-claim-spec-operand-binding-report.json"

def load_candidate():
    path=CAP/"objective_claim_operand_binding.py"
    spec=importlib.util.spec_from_file_location("pr444_candidate",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def extraction(left_text,right_text,url="https://qualification.example/evidence"):
    page=sha(("page:"+left_text+"|"+right_text).encode())
    texts=[left_text,right_text]
    visible_text="\n".join(texts)
    visible=sha(visible_text)
    rows=[]
    cursor=0
    for text in texts:
        text_sha=sha(text)
        start=cursor
        end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{text_sha}")
        rows.append({
            "evidence_unit_id":uid,
            "source_url":url,
            "page_raw_sha256":page,
            "visible_text_sha256":visible,
            "text":text,
            "text_sha256":text_sha,
            "visible_text_start":start,
            "visible_text_end":end,
        })
        cursor=end+1
    return {
        "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
        "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
        "output_verified":True,
        "source_url":url,
        "page_raw_sha256":page,
        "visible_text_sha256":visible,
        "evidence_units":rows,
    }

def assert_equal(actual,expected,label):
    if actual!=expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")

def assert_contains(text,needle,label):
    if needle.lower() not in text.lower():
        raise AssertionError(f"{label}: {needle!r} not in {text!r}")

def decimal_relation(left,right,op):
    l=Decimal(left); r=Decimal(right)
    return {"GT":l>r,"LT":l<r}[op]

def run_positive(candidate,case):
    data=extraction(case["left_text"],case["right_text"],case["url"])
    out=candidate.bind(case["objective"],data,evaluate_relation=True)
    assert_equal(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",case["id"]+" status")
    assert_equal(out["relation_spec"]["operator"],case["operator"],case["id"]+" operator")
    assert_contains(out["left_binding"]["text"],case["left_anchor"],case["id"]+" left role")
    assert_contains(out["right_binding"]["text"],case["right_anchor"],case["id"]+" right role")
    assert_equal(out["operand_pair"]["left_surface"].rstrip(".,;:"),case["left_surface"].rstrip(".,;:"),case["id"]+" left surface")
    assert_equal(out["operand_pair"]["right_surface"].rstrip(".,;:"),case["right_surface"].rstrip(".,;:"),case["id"]+" right surface")
    expected=decimal_relation(case["left_number"],case["right_number"],case["operator"])
    assert_equal(out["relation_result"]["predicate"],expected,case["id"]+" predicate")
    assert_equal(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",case["id"]+" relation status")
    assert_equal(out["factual_correctness_status"],"UNVERIFIED",case["id"]+" truth scope")
    assert_equal(out["semantic_entailment_status"],"UNVERIFIED",case["id"]+" entailment scope")
    assert_equal(out["model_dependency_count"],0,case["id"]+" model dependency")
    return {
        "id":case["id"],
        "operator":out["relation_spec"]["operator"],
        "predicate":out["relation_result"]["predicate"],
        "left_surface":out["operand_pair"]["left_surface"],
        "right_surface":out["operand_pair"]["right_surface"],
        "left_unit":out["operand_pair"]["unit_surface"],
        "status":"PASS",
    }

def run_negatives(candidate):
    checks=[]

    base=extraction(
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    )
    out=candidate.bind("Compare France and Germany population growth.",base,evaluate_relation=False)
    assert_equal(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED","unsupported objective")
    checks.append({"id":"UNSUPPORTED_OBJECTIVE","status":"PASS"})

    dup=extraction(
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    )
    first=dict(dup["evidence_units"][0])
    first["visible_text_start"]=200
    first["visible_text_end"]=200+len(first["text"])
    first["evidence_unit_id"]=sha(f'{dup["page_raw_sha256"]}:{first["visible_text_start"]}:{first["visible_text_end"]}:{first["text_sha256"]}')
    dup["evidence_units"].append(first)
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        dup,evaluate_relation=False
    )
    assert_equal(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY","ambiguous role")
    checks.append({"id":"AMBIGUOUS_ROLE","status":"PASS"})

    multi=extraction(
        "France population growth was 0.35 percent and revised to 0.40 percent.",
        "Germany population growth was -0.10 percent.",
    )
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        multi,evaluate_relation=False
    )
    assert_equal(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR","multiple numeric candidates")
    checks.append({"id":"MULTIPLE_NUMBERS","status":"PASS"})

    mismatch=extraction(
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 points.",
    )
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        mismatch,evaluate_relation=False
    )
    assert_equal(out["reason"],"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR","unit mismatch")
    checks.append({"id":"UNIT_MISMATCH","status":"PASS"})

    tampered=extraction(
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    )
    tampered["evidence_units"][0]["text"]+=" altered"
    try:
        candidate.bind(
            "Determine whether France population growth is higher than Germany population growth.",
            tampered,evaluate_relation=True
        )
    except ValueError as exc:
        if not any(k in str(exc) for k in ("TEXT_HASH_MISMATCH","OFFSET_INVALID")):
            raise
    else:
        raise AssertionError("tampered evidence unexpectedly accepted")
    checks.append({"id":"TAMPERED_EVIDENCE","status":"PASS"})

    return checks

def main():
    candidate=load_candidate()
    cases=[
        {
            "id":"CLIMATE_GT_TRUE",
            "objective":"Determine whether Arctic temperature anomaly is higher than Antarctic temperature anomaly.",
            "left_text":"Arctic temperature anomaly was 1.24 degrees.",
            "right_text":"Antarctic temperature anomaly was 0.87 degrees.",
            "left_anchor":"Arctic temperature anomaly",
            "right_anchor":"Antarctic temperature anomaly",
            "left_surface":"1.24 degrees",
            "right_surface":"0.87 degrees",
            "left_number":"1.24","right_number":"0.87","operator":"GT",
            "url":"https://climate.example/evidence",
        },
        {
            "id":"MATERIALS_LT_TRUE",
            "objective":"Determine whether Alloy Beta yield strength is lower than Alloy Alpha yield strength.",
            "left_text":"Alloy Beta yield strength was 410 MPa.",
            "right_text":"Alloy Alpha yield strength was 520 MPa.",
            "left_anchor":"Alloy Beta yield strength",
            "right_anchor":"Alloy Alpha yield strength",
            "left_surface":"410 MPa",
            "right_surface":"520 MPa",
            "left_number":"410","right_number":"520","operator":"LT",
            "url":"https://materials.example/evidence",
        },
        {
            "id":"ASTRONOMY_GT_FALSE",
            "objective":"Planet Kepler A orbital period exceeds Planet Kepler B orbital period.",
            "left_text":"Planet Kepler A orbital period was 120 days.",
            "right_text":"Planet Kepler B orbital period was 180 days.",
            "left_anchor":"Planet Kepler A orbital period",
            "right_anchor":"Planet Kepler B orbital period",
            "left_surface":"120 days",
            "right_surface":"180 days",
            "left_number":"120","right_number":"180","operator":"GT",
            "url":"https://astronomy.example/evidence",
        },
        {
            "id":"ECONOMICS_EXCEED_TRUE",
            "objective":"Does Egypt inflation exceed Morocco inflation?",
            "left_text":"Egypt inflation was 9.2 percent.",
            "right_text":"Morocco inflation was 3.4 percent.",
            "left_anchor":"Egypt inflation",
            "right_anchor":"Morocco inflation",
            "left_surface":"9.2 percent",
            "right_surface":"3.4 percent",
            "left_number":"9.2","right_number":"3.4","operator":"GT",
            "url":"https://economics.example/evidence",
        },
    ]
    report={
        "schema":"PROJECT_BRAIN_PR444_INDEPENDENT_QUALIFICATION_V1",
        "candidate_scope":"BOUNDED_EXPLICIT_BINARY_COMPARISON_WITH_UNIQUE_LEXICAL_ROLE_BINDING",
        "positive_checks":[],
        "negative_checks":[],
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    for case in cases:
        report["positive_checks"].append(run_positive(candidate,case))
    report["negative_checks"]=run_negatives(candidate)
    report["status"]="PASS"
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
