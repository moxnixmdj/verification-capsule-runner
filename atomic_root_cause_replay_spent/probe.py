#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import statistics
from pathlib import Path
from typing import Any

from agent_replay import AblationEngine, ReplayPlan, find_minimal_repair, record

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / "cases.json").read_text())


def execute(route_id: str, payload: dict[str, Any]) -> str:
    if route_id == "sum_numbers":
        return str(round(sum(payload["numbers"]), 10))
    if route_id == "mean_numbers":
        return str(float(sum(payload["numbers"]) / len(payload["numbers"])))
    if route_id == "median_numbers":
        return str(float(statistics.median(payload["numbers"])))
    if route_id == "max_number":
        return str(max(payload["numbers"]))
    if route_id == "sort_numbers":
        return ",".join(str(x) for x in sorted(payload["numbers"]))
    if route_id == "unique_items":
        return ",".join(dict.fromkeys(payload["items"]))
    if route_id == "count_words":
        return str(len(payload["text"].split()))
    if route_id == "basename_path":
        return os.path.basename(payload["path"])
    if route_id == "extension_path":
        return os.path.splitext(payload["path"])[1]
    if route_id == "json_key":
        return str(payload["object"][payload["key"]])
    if route_id == "sha256_text":
        return hashlib.sha256(payload["text"].encode()).hexdigest()
    raise KeyError(route_id)


def safe_execute(route_id: str, payload: dict[str, Any]) -> str:
    try:
        return execute(route_id, payload)
    except Exception as exc:
        return f"TOOL_ERROR:{type(exc).__name__}"


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    selected_route = case["selected_route"]
    expected_route = case["expected_route"]
    expected_output = case["expected_output"]

    def agent(ctx, query: str, payload: dict[str, Any]) -> dict[str, Any]:
        route = ctx.tool(
            "route_selection",
            produce=lambda: selected_route,
            query=query,
        )
        output = ctx.tool(
            "execute_selected_route",
            produce=lambda: safe_execute(route, payload),
            route_id=route,
            payload=payload,
        )
        return {"route": route, "output": output}

    def verifier(result: dict[str, Any]) -> float:
        return 1.0 if (
            result["route"] == expected_route
            and result["output"] == expected_output
        ) else 0.0

    task = {"query": case["query"], "payload": case["payload"]}
    traj = record(
        agent,
        task,
        session_id=case["id"],
        seed=11,
        verifier=verifier,
    )
    engine = AblationEngine(agent, traj, verifier, base_seed=1000)

    factual_fail = bool(engine.factual_fail(1)[0])
    candidate_routes = [r for r in case["routes"] if r != selected_route]

    intervention_rows = []
    for i, cand in enumerate(candidate_routes):
        fails = engine.run_plan(
            ReplayPlan(held=set(), forced={0: cand}),
            1,
            seed_tag=100 + i,
        )
        intervention_rows.append({
            "candidate_route": cand,
            "terminal_fail": bool(fails[0]),
            "terminal_success": not bool(fails[0]),
        })

    rescuing_routes = [
        row["candidate_route"]
        for row in intervention_rows
        if row["terminal_success"]
    ]

    # Negative control: repair only the downstream executor output while keeping
    # the original wrong route. The original terminal contract requires both the
    # correct route and correct output, so symptom-only repair must remain failed.
    downstream_only_fail = bool(
        engine.run_plan(
            ReplayPlan(held={0}, forced={1: expected_output}),
            1,
            seed_tag=777,
        )[0]
    )

    repair = find_minimal_repair(
        engine,
        0,
        rollouts=1,
        candidates={0: candidate_routes},
    )

    localized = (
        factual_fail
        and len(rescuing_routes) >= 1
        and downstream_only_fail
        and repair is not None
        and repair.valid
    )

    return {
        "id": case["id"],
        "factual_selected_route": selected_route,
        "candidate_count": len(candidate_routes),
        "factual_fail": factual_fail,
        "interventions": intervention_rows,
        "rescuing_routes": rescuing_routes,
        "unique_rescue": len(rescuing_routes) == 1,
        "downstream_output_only_repair_still_fails": downstream_only_fail,
        "agent_replay_repair": repair.to_dict() if repair else None,
        "route_step_causally_localized": localized,
        # Evaluation-only disclosure after the causal search. This value never
        # participates in candidate generation.
        "evaluation_expected_route": expected_route,
        "repair_matches_evaluation_route": (
            repair is not None and repair.repaired_action == expected_route
        ),
    }


def main() -> int:
    rows = [run_case(c) for c in CASES["cases"]]
    n = len(rows)
    localized = sum(r["route_step_causally_localized"] for r in rows)
    unique = sum(r["unique_rescue"] for r in rows)
    matches = sum(r["repair_matches_evaluation_route"] for r in rows)

    result = {
        "schema": "PROJECT_BRAIN_ATOMIC_CAUSAL_REPLAY_SPENT_C3_RESULT_V1",
        "status": "SPENT_CAUSAL_FALSIFICATION_SCREEN__ZERO_CAPABILITY_CREDIT",
        "candidate": {
            "repo": "krishddd/Trajectory_Causal_Attribution",
            "package": "trajectory-causal-attribution",
            "version": "1.0.0",
            "license": "MIT",
        },
        "mechanism_under_test": "CAUSE_HYPOTHESIS_EXECUTABLE_FALSIFICATION",
        "candidate_generation_policy": "EXHAUSTIVE_ENUMERATION_OF_ADMISSIBLE_ROUTE_ACTIONS_FROM_FROZEN_EPISODE__NO_EXPECTED_ROUTE_INPUT",
        "cases": n,
        "route_step_causal_localization_accuracy": localized / n,
        "unique_rescue_fraction": unique / n,
        "repair_matches_evaluation_route_fraction": matches / n,
        "all_factual_runs_failed": all(r["factual_fail"] for r in rows),
        "all_downstream_symptom_only_repairs_failed": all(
            r["downstream_output_only_repair_still_fails"] for r in rows
        ),
        "rows": rows,
        "interpretation_rule": "PASS_ONLY_ESTABLISHES_EXECUTABLE_CAUSAL_FALSIFICATION_ON_SPENT_C3_TRACES__IT_DOES_NOT_SOLVE_CAUSE_CANDIDATE_GENERATION_OR_GENERAL_ROOT_CAUSE_LOCALIZATION",
        "capability_credit_delta": 0,
    }
    (HERE / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "cases": n,
        "route_step_causal_localization_accuracy": result["route_step_causal_localization_accuracy"],
        "unique_rescue_fraction": result["unique_rescue_fraction"],
        "repair_matches_evaluation_route_fraction": result["repair_matches_evaluation_route_fraction"],
        "all_downstream_symptom_only_repairs_failed": result["all_downstream_symptom_only_repairs_failed"],
    }, indent=2))
    return 0 if localized == n and matches == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
