#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"pr447-claim-spec-operand-binding-report.json"

def load_candidate():
    path=CAP/"objective_claim_operand_binding.py"
    spec=importlib.util.spec_from_file_location("pr447_candidate",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def extraction(texts,url="https://qualification.example/evidence"):
    page=sha(("page|"+"|".join(texts)).encode())
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

def eq(actual,expected,label):
    if actual!=expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")

def contains(text,needle,label):
    if needle.lower() not in text.lower():
        raise AssertionError(f"{label}: {needle!r} not in {text!r}")

def decimal_pred(left,right,op,threshold=None):
    l=Decimal(left); r=Decimal(right)
    if op=="GT": return l>r
    if op=="LT": return l<r
    if op=="GTE": return l>=r
    if op=="LTE": return l<=r
    if op=="EQ": return l==r
    if op=="NE": return l!=r
    if op=="ABS_DIFF_LTE":
        return abs(l-r)<=Decimal(threshold)
    raise AssertionError(op)

def relation_case(candidate,case):
    data=extraction([case["left_text"],case["right_text"]],case["url"])
    out=candidate.bind(case["objective"],data,evaluate_relation=True)
    eq(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",case["id"]+" status")
    eq(out["relation_spec"]["operator"],case["operator"],case["id"]+" operator")
    contains(out["left_binding"]["text"],case["left_anchor"],case["id"]+" left role")
    contains(out["right_binding"]["text"],case["right_anchor"],case["id"]+" right role")
    expected=decimal_pred(case["left_number"],case["right_number"],case["operator"],case.get("threshold_number"))
    eq(out["relation_result"]["predicate"],expected,case["id"]+" predicate")
    eq(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",case["id"]+" relation status")
    if case.get("threshold_surface") is not None:
        eq(out["relation_spec"]["threshold"].rstrip(".,;:"),case["threshold_surface"].rstrip(".,;:"),case["id"]+" threshold")
    eq(out["semantic_entailment_status"],"UNVERIFIED",case["id"]+" entailment scope")
    eq(out["factual_correctness_status"],"UNVERIFIED",case["id"]+" truth scope")
    eq(out["model_dependency_count"],0,case["id"]+" model dependency")
    return {
        "id":case["id"],
        "operator":case["operator"],
        "predicate":out["relation_result"]["predicate"],
        "left_role":out["left_binding"]["text"],
        "right_role":out["right_binding"]["text"],
        "status":"PASS",
    }

def quoted_case(candidate):
    claim="The protocol retry interval is 5 seconds."
    data=extraction([
        claim,
        "Administrative reference text says the revision date is 2026."
    ],"https://software.example/evidence")
    out=candidate.bind(
        'Verify whether the evidence states "The protocol retry interval is 5 seconds."',
        data,
        evaluate_relation=True,
    )
    eq(out["status"],"CLAIM_SPEC_BOUND","quoted status")
    eq(out["relation_spec"]["mode"],"VERBATIM_SUPPORT","quoted mode")
    eq(out["relation_result"]["status"],"EXACT_TEXT_SUPPORT_VERIFIED","quoted result")
    eq(len(out["relation_result"]["matches"]),1,"quoted unique match")
    eq(out["semantic_entailment_status"],"UNVERIFIED","quoted entailment scope")
    return {"id":"SOFTWARE_EXACT_QUOTED_SUPPORT","status":"PASS"}

def negatives(candidate):
    checks=[]

    data=extraction([
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    ])
    out=candidate.bind("Compare France and Germany population growth.",data,evaluate_relation=False)
    eq(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED","unsupported language")
    checks.append({"id":"UNSUPPORTED_LANGUAGE","status":"PASS"})

    dup=extraction([
        "The protocol retry interval is 5 seconds.",
        "The protocol retry interval is 5 seconds.",
    ])
    out=candidate.bind(
        'Verify the exact claim "retry interval is 5 seconds."',
        dup,
        evaluate_relation=False,
    )
    eq(out["reason"],"EXACT_QUOTED_CLAIM_EVIDENCE_AMBIGUOUS","duplicate exact claim")
    checks.append({"id":"DUPLICATE_EXACT_CLAIM","status":"PASS"})

    multi=extraction([
        "France population growth was 0.35 percent and revised to 0.40 percent.",
        "Germany population growth was -0.10 percent.",
    ])
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        multi,
        evaluate_relation=False,
    )
    eq(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR","multiple values")
    checks.append({"id":"MULTIPLE_COMPATIBLE_VALUES","status":"PASS"})

    mismatch=extraction([
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 points.",
    ])
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        mismatch,
        evaluate_relation=False,
    )
    eq(out["reason"],"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR","unit mismatch")
    checks.append({"id":"UNIT_MISMATCH","status":"PASS"})

    threshold=extraction([
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    ])
    try:
        candidate.bind(
            "Determine whether France population growth and Germany population growth differ by at most 0.5 points.",
            threshold,
            evaluate_relation=True,
        )
    except ValueError as exc:
        if "THRESHOLD_UNIT_MISMATCH" not in str(exc):
            raise
    else:
        raise AssertionError("threshold unit mismatch unexpectedly accepted")
    checks.append({"id":"THRESHOLD_UNIT_MISMATCH","status":"PASS"})

    collision=extraction([
        "France population growth 0.35 percent and Germany population growth -0.10 percent.",
        "Administrative reference text was 1 percent.",
    ])
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        collision,
        evaluate_relation=False,
    )
    eq(out["reason"],"LEFT_RIGHT_ROLE_COLLISION","role collision")
    checks.append({"id":"ROLE_COLLISION","status":"PASS"})

    ambiguous=extraction([
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    ])
    clone=dict(ambiguous["evidence_units"][0])
    clone["visible_text_start"]=200
    clone["visible_text_end"]=200+len(clone["text"])
    clone["evidence_unit_id"]=sha(f'{ambiguous["page_raw_sha256"]}:{clone["visible_text_start"]}:{clone["visible_text_end"]}:{clone["text_sha256"]}')
    ambiguous["evidence_units"].append(clone)
    out=candidate.bind(
        "Determine whether France population growth is higher than Germany population growth.",
        ambiguous,
        evaluate_relation=False,
    )
    eq(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY","ambiguous role")
    checks.append({"id":"AMBIGUOUS_ROLE","status":"PASS"})

    tampered=extraction([
        "France population growth was 0.35 percent.",
        "Germany population growth was -0.10 percent.",
    ])
    tampered["evidence_units"][0]["text"]+=" altered"
    try:
        candidate.bind(
            "Determine whether France population growth is higher than Germany population growth.",
            tampered,
            evaluate_relation=True,
        )
    except ValueError as exc:
        if not any(x in str(exc) for x in ("TEXT_HASH_MISMATCH","OFFSET_INVALID")):
            raise
    else:
        raise AssertionError("tampered evidence unexpectedly accepted")
    checks.append({"id":"TAMPERED_EVIDENCE","status":"PASS"})

    return checks

def main():
    candidate=load_candidate()
    cases=[
        {
            "id":"ECONOMICS_GT_TRUE",
            "objective":"Does Egypt inflation exceed Morocco inflation?",
            "left_text":"Egypt inflation was 9.2 percent.",
            "right_text":"Morocco inflation was 3.4 percent.",
            "left_anchor":"Egypt inflation","right_anchor":"Morocco inflation",
            "left_number":"9.2","right_number":"3.4","operator":"GT",
            "url":"https://economics.example/evidence",
        },
        {
            "id":"MATERIALS_LT_TRUE",
            "objective":"Determine whether Alloy Beta yield strength is lower than Alloy Alpha yield strength.",
            "left_text":"Alloy Beta yield strength was 410 MPa.",
            "right_text":"Alloy Alpha yield strength was 520 MPa.",
            "left_anchor":"Alloy Beta yield strength","right_anchor":"Alloy Alpha yield strength",
            "left_number":"410","right_number":"520","operator":"LT",
            "url":"https://materials.example/evidence",
        },
        {
            "id":"CHEMISTRY_GTE_TRUE",
            "objective":"Determine whether Solution Alpha concentration is at least Solution Beta concentration.",
            "left_text":"Solution Alpha concentration was 7.1 mol.",
            "right_text":"Solution Beta concentration was 7.0 mol.",
            "left_anchor":"Solution Alpha concentration","right_anchor":"Solution Beta concentration",
            "left_number":"7.1","right_number":"7.0","operator":"GTE",
            "url":"https://chemistry.example/evidence",
        },
        {
            "id":"NETWORK_LTE_TRUE",
            "objective":"Determine whether Link East latency is at most Link West latency.",
            "left_text":"Link East latency was 25 ms.",
            "right_text":"Link West latency was 30 ms.",
            "left_anchor":"Link East latency","right_anchor":"Link West latency",
            "left_number":"25","right_number":"30","operator":"LTE",
            "url":"https://network.example/evidence",
        },
        {
            "id":"PHYSICS_EQ_TRUE",
            "objective":"Determine whether Sensor Red voltage is equal to Sensor Blue voltage.",
            "left_text":"Sensor Red voltage was 5.0 V.",
            "right_text":"Sensor Blue voltage was 5.0 V.",
            "left_anchor":"Sensor Red voltage","right_anchor":"Sensor Blue voltage",
            "left_number":"5.0","right_number":"5.0","operator":"EQ",
            "url":"https://physics.example/evidence",
        },
        {
            "id":"ENERGY_NE_TRUE",
            "objective":"Determine whether Reactor North output is different from Reactor South output.",
            "left_text":"Reactor North output was 910 MW.",
            "right_text":"Reactor South output was 875 MW.",
            "left_anchor":"Reactor North output","right_anchor":"Reactor South output",
            "left_number":"910","right_number":"875","operator":"NE",
            "url":"https://energy.example/evidence",
        },
        {
            "id":"CLIMATE_ABS_DIFF_TRUE",
            "objective":"Determine whether Station North anomaly and Station South anomaly differ by at most 0.5 degrees.",
            "left_text":"Station North anomaly was 1.24 degrees.",
            "right_text":"Station South anomaly was 0.87 degrees.",
            "left_anchor":"Station North anomaly","right_anchor":"Station South anomaly",
            "left_number":"1.24","right_number":"0.87","operator":"ABS_DIFF_LTE",
            "threshold_number":"0.5","threshold_surface":"0.5 degrees",
            "url":"https://climate.example/evidence",
        },
        {
            "id":"ASTRONOMY_SINGLE_LABEL_GT_FALSE",
            "objective":"Planet Kepler A orbital period exceeds Planet Kepler B orbital period.",
            "left_text":"Planet Kepler A orbital period was 120 days.",
            "right_text":"Planet Kepler B orbital period was 180 days.",
            "left_anchor":"Kepler A","right_anchor":"Kepler B",
            "left_number":"120","right_number":"180","operator":"GT",
            "url":"https://astronomy.example/evidence",
        },
    ]
    report={
        "schema":"PROJECT_BRAIN_PR447_INDEPENDENT_QUALIFICATION_V1",
        "candidate_scope":"BOUNDED_EXPLICIT_COMPARISONS_FULL_OPERATOR_SURFACE_PLUS_EXACT_QUOTED_SUPPORT",
        "positive_checks":[],
        "negative_checks":[],
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    try:
        for case in cases:
            report["positive_checks"].append(relation_case(candidate,case))
        report["positive_checks"].append(quoted_case(candidate))
        report["negative_checks"]=negatives(candidate)
        report["status"]="PASS"
    except Exception as exc:
        report["status"]="FAIL"
        report["error_class"]=type(exc).__name__
        report["error"]=str(exc)
        REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
