#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from brain_owned_candidate import CausalTraceError, intervenable_decision_ancestors

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / "cases.json").read_text())
DONOR = json.loads((HERE / "result.json").read_text())


def main() -> int:
    donor_by_id = {row["id"]: row for row in DONOR["rows"]}
    rows = []
    for case in CASES["cases"]:
        got = intervenable_decision_ancestors(case["events"], case["target"])
        donor = donor_by_id[case["id"]]["candidate_events"]
        expected = case["expected_cause_event"]
        rows.append({
            "id": case["id"],
            "brain_owned_candidates": got,
            "donor_candidates": donor,
            "exact_donor_equivalence": got == donor,
            "contains_expected_cause": expected in got,
            "unique_expected_candidate": got == [expected],
        })

    structural_checks = {}

    try:
        intervenable_decision_ancestors(
            [{"id":"a","role":"decision","intervenable":True,"caused_by":["missing"]}],
            "a",
        )
        structural_checks["unknown_parent_fail_closed"] = False
    except CausalTraceError:
        structural_checks["unknown_parent_fail_closed"] = True

    try:
        intervenable_decision_ancestors(
            [
                {"id":"a","role":"decision","intervenable":True,"caused_by":["b"]},
                {"id":"b","role":"decision","intervenable":True,"caused_by":["a"]},
            ],
            "a",
        )
        structural_checks["cycle_fail_closed"] = False
    except CausalTraceError:
        structural_checks["cycle_fail_closed"] = True

    try:
        intervenable_decision_ancestors(
            [{"id":"a","role":"decision","intervenable":True,"caused_by":[]}],
            "missing",
        )
        structural_checks["unknown_target_fail_closed"] = False
    except CausalTraceError:
        structural_checks["unknown_target_fail_closed"] = True

    result = {
        "schema":"PROJECT_BRAIN_CAUSE_CANDIDATE_DONOR_DELETION_VERIFICATION_V1",
        "status":"DONOR_DELETION_EQUIVALENCE_SCREEN__ZERO_CAPABILITY_CREDIT",
        "source_candidate":"atomic_cause_candidate_spent/brain_owned_candidate.py",
        "donor":{
            "repo":"ShaneDolphin/pyrapide",
            "revision":"d1dc66efbefe3442e247ac896416bf00c25d3ca1",
            "license":"MIT",
            "mechanism":"BACKWARD_CAUSAL_SLICE_PLUS_INTERVENABLE_DECISION_FILTER",
        },
        "cases":len(rows),
        "exact_donor_equivalence_fraction":sum(r["exact_donor_equivalence"] for r in rows)/len(rows),
        "true_cause_recall":sum(r["contains_expected_cause"] for r in rows)/len(rows),
        "unique_expected_candidate_fraction":sum(r["unique_expected_candidate"] for r in rows)/len(rows),
        "donor_imported_by_candidate":False,
        "external_runtime_dependencies":[],
        "structural_fail_closed_checks":structural_checks,
        "rows":rows,
        "interpretation_rule":"PASS_PROVES_ONLY_DONOR_INDEPENDENT_EQUIVALENCE_FOR_THE_SCREENED_EXPLICIT_CAUSAL_GRAPH_CONTRACT__NOT_GENERAL_CAUSAL_DISCOVERY",
        "capability_credit_delta":0,
    }
    (HERE/"brain_owned_result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({
        "cases":result["cases"],
        "exact_donor_equivalence_fraction":result["exact_donor_equivalence_fraction"],
        "true_cause_recall":result["true_cause_recall"],
        "unique_expected_candidate_fraction":result["unique_expected_candidate_fraction"],
        "structural_fail_closed_checks":structural_checks,
    },indent=2))
    ok = (
        result["exact_donor_equivalence_fraction"] == 1.0
        and result["true_cause_recall"] == 1.0
        and result["unique_expected_candidate_fraction"] == 1.0
        and all(structural_checks.values())
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
