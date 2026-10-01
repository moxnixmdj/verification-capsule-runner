#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from pyrapide import Computation, Event
from pyrapide.analysis.queries import backward_slice

HERE = Path(__file__).resolve().parent
CAPSULE = json.loads((HERE / "cases.json").read_text())


def generate_candidates(case):
    comp = Computation()
    events = {}
    for raw in case["events"]:
        event = Event(
            id=raw["id"],
            name=raw["name"],
            source=raw["role"],
            metadata={
                "role": raw["role"],
                "intervenable": bool(raw["intervenable"]),
            },
        )
        causes = [events[c] for c in raw.get("caused_by", [])]
        comp.record(event, caused_by=causes or None)
        events[raw["id"]] = event

    target = events[case["target"]]
    causal_slice = backward_slice(comp, target)

    # Candidate generation uses only causal ancestry + explicit event capability
    # metadata. Evaluation labels are intentionally not in this function.
    candidates = sorted(
        e.id
        for e in causal_slice.events
        if e.id != target.id
        and bool(e.metadata.get("intervenable"))
        and e.metadata.get("role") == "decision"
    )
    all_upstream = sorted(e.id for e in causal_slice.events if e.id != target.id)
    return candidates, all_upstream


def main():
    rows = []
    for case in CAPSULE["cases"]:
        candidates, all_upstream = generate_candidates(case)
        expected = case["expected_cause_event"]  # evaluation only, after generation
        rows.append({
            "id": case["id"],
            "candidate_events": candidates,
            "candidate_count": len(candidates),
            "all_upstream_event_count": len(all_upstream),
            "expected_cause_event": expected,
            "contains_expected_cause": expected in candidates,
            "unique_expected_candidate": candidates == [expected],
            "selectivity_fraction_vs_all_upstream": (
                len(candidates) / len(all_upstream) if all_upstream else 0.0
            ),
        })

    n = len(rows)
    recall = sum(r["contains_expected_cause"] for r in rows) / n
    unique = sum(r["unique_expected_candidate"] for r in rows) / n
    mean_selectivity = sum(r["selectivity_fraction_vs_all_upstream"] for r in rows) / n

    result = {
        "schema": "PROJECT_BRAIN_CAUSE_CANDIDATE_GENERATION_SPENT_RESULT_V1",
        "status": "SPENT_CAUSE_CANDIDATE_GENERATION_SCREEN__ZERO_CAPABILITY_CREDIT",
        "candidate": {
            "repo": "ShaneDolphin/pyrapide",
            "revision": "d1dc66efbefe3442e247ac896416bf00c25d3ca1",
            "license": "MIT",
            "mechanism": "BACKWARD_CAUSAL_SLICE_PLUS_INTERVENABLE_DECISION_FILTER",
        },
        "cases": n,
        "true_cause_candidate_recall": recall,
        "unique_expected_candidate_fraction": unique,
        "mean_candidate_fraction_vs_all_upstream": mean_selectivity,
        "generator_inputs": "CAUSAL_EDGES_PLUS_EVENT_ROLE_AND_INTERVENABLE_METADATA_ONLY",
        "expected_cause_leakage": False,
        "rows": rows,
        "interpretation_rule": (
            "PASS_ESTABLISHES_ONLY_DETERMINISTIC_CANDIDATE_GENERATION_FOR_TRACES_WITH_"
            "EXPLICIT_CAUSAL_EDGES_AND_INTERVENABLE_DECISION_METADATA__NOT_GENERAL_CAUSAL_DISCOVERY"
        ),
        "capability_credit_delta": 0,
    }
    (HERE / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "cases": n,
        "true_cause_candidate_recall": recall,
        "unique_expected_candidate_fraction": unique,
        "mean_candidate_fraction_vs_all_upstream": mean_selectivity,
    }, indent=2))
    return 0 if recall == 1.0 and unique == 1.0 and mean_selectivity < 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
