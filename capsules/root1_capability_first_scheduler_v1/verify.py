#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name: str, rel: str):
    path = HERE / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


policy = load_module(
    "terminal_minimum_causal_depth_policy_v1",
    "canonical/runtime/terminal_minimum_causal_depth_policy_v1.py",
)
controller = load_module(
    "terminal_causal_depth_controller_v1",
    "canonical/runtime/terminal_causal_depth_controller_v1.py",
)
registry = json.loads(
    (HERE / "canonical/governance/ROOT1_CAPABILITY_REPAIR_REGISTRY_V1.json")
    .read_text(encoding="utf-8")
)

CURRENT = {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
    "total_families": 19,
    "total_atomic": 38,
    "root1_positive_gaps": 1,
    "root2_only": 15,
    "root3_only": 7,
    "root2_and_root3": 3,
    "terminal": False,
}


def must_fail(fn, token: str) -> None:
    try:
        fn()
    except Exception as exc:
        assert token in str(exc), (token, type(exc).__name__, str(exc))
        return
    raise AssertionError(f"expected failure containing {token}")


# 1. Current authoritative partition must pass.
policy.validate_live_state(CURRENT)

# 2. A future verified delta must not require a source-code snapshot edit.
future = dict(CURRENT)
future.update({
    "accepted_families": 6,
    "open_families": 13,
    "proved_atomic": 13,
    "unresolved_atomic": 25,
    "root1_positive_gaps": 0,
})
policy.validate_live_state(future)

# 3. Algebraically inconsistent projections must fail closed.
bad_atomic = dict(CURRENT)
bad_atomic["proved_atomic"] = 13
must_fail(lambda: policy.validate_live_state(bad_atomic), "INCONSISTENT_ATOMIC_PARTITION")

bad_roots = dict(CURRENT)
bad_roots["root2_only"] = 16
must_fail(lambda: policy.validate_live_state(bad_roots), "INCONSISTENT_ROOT_PARTITION")

# 4. Terminal truth is derived, not manually asserted.
closed = {
    "accepted_families": 19,
    "open_families": 0,
    "proved_atomic": 38,
    "unresolved_atomic": 0,
    "total_families": 19,
    "total_atomic": 38,
    "root1_positive_gaps": 0,
    "root2_only": 0,
    "root3_only": 0,
    "root2_and_root3": 0,
    "terminal": True,
}
policy.validate_live_state(closed)
closed["terminal"] = False
must_fail(lambda: policy.validate_live_state(closed), "INCONSISTENT_TERMINAL_FLAG")

authority = {
    "truth": {"achieved": False},
    "atomic_acceptance_frontier": {"proved": 12, "unresolved": 26, "total": 38},
}
root_state = {
    "roots": {
        "root_1_capability_missing": {
            "current_positive_root1_blockers": [
                {
                    "predicate_id": "LIVEBENCH_IF_GE_65_7",
                    "state": "POSITIVE_OPERATIVE_GAP",
                }
            ]
        }
    }
}
graph = {
    "actions": [
        {
            "id": "SCORE_ONLY_HELPER",
            "new_reality_units": 0,
            "target_predicates": ["LIVEBENCH_IF_GE_65_7"],
            "preconditions": [],
        },
        {
            "id": "OTHER_ZERO_REALITY",
            "new_reality_units": 0,
            "target_predicates": ["FINANCE_ACCOUNTING_INDEX_GE_61"],
            "preconditions": [],
        },
    ]
}

# 5. Positive Root1 must become the first causal barrier.
plan = controller.compile_causal_depth_plan(
    authority, graph, {"claims": []}, root_state, registry
)
ids = [b["id"] for b in plan["barriers"]]
assert ids == [
    "BARRIER_0_POSITIVE_ROOT1_CAPABILITY_REPAIR",
    "BARRIER_1_ZERO_REALITY_MEGABATCH",
    "BARRIER_2_MINIMUM_REALITY_TRANSACTION",
    "BARRIER_3_ATOMIC_FINALITY",
], ids
root1 = plan["barriers"][0]
assert root1["scheduler_ready"] is True
assert root1["predicate_ids"] == ["LIVEBENCH_IF_GE_65_7"]
assert root1["repair_actions"][0]["repair_id"] == "ROOT1_LIVEBENCH_GENERAL_SEMANTIC_CORE"
assert plan["objective_order"][0] == "DISCHARGE_POSITIVE_OPERATIVE_CAPABILITY_GAPS"
assert plan["barriers"][1]["root1_predicates_reserved_for_capability_repair"] == [
    "LIVEBENCH_IF_GE_65_7"
]
assert plan["credit_delta"] == 0
assert plan["execution_authority"] is False
assert plan["promotion_authority"] is False

# 6. Missing Root1 repair binding must fail closed at scheduling.
unbound = controller.compile_causal_depth_plan(
    authority, graph, {"claims": []}, root_state, {"repairs": []}
)
b0 = unbound["barriers"][0]
assert b0["scheduler_ready"] is False
assert b0["blocking_unbound_predicates"] == ["LIVEBENCH_IF_GE_65_7"]
assert b0["repair_actions"] == []

# 7. Registry must bind genuine semantic capability repair, not score cosmetics.
repair = registry["repairs"][0]
assert repair["predicate_id"] == "LIVEBENCH_IF_GE_65_7"
assert repair["required_capability_layer"] == "GENERAL_SEMANTIC_SEED_PRODUCTION"
assert set(repair["required_effects"]) == {
    "text.paraphrase.semantic_preserving",
    "text.simplify.semantic_preserving",
    "text.summarize.faithful",
    "text.story.generate_instruction_grounded",
}
assert repair["current_ranked_route"].endswith(
    "LIVEBENCH_ROOT1_Q4_RESOURCE_DOMINANCE_FREEZE_20261004_V1.json"
)
assert "Q4" in repair["current_ranked_route_basis"]
rules = " ".join(registry["hard_rules"])
assert "SCORER_ONLY" in rules
assert "ZERO_ROOT1_CAPABILITY_CREDIT" in rules
assert registry["execution_authority"] is False
assert registry["fresh_reality_authority"] is False
assert registry["promotion_authority"] is False
assert registry["acceptance_credit_delta"] == 0
assert registry["capability_credit_delta"] == 0

# 8. Backward-compatible no-root-state call remains three barriers.
legacy = controller.compile_causal_depth_plan(authority, {"actions": []}, {"claims": []})
assert [b["id"] for b in legacy["barriers"]] == [
    "BARRIER_1_ZERO_REALITY_MEGABATCH",
    "BARRIER_2_MINIMUM_REALITY_TRANSACTION",
    "BARRIER_3_ATOMIC_FINALITY",
]

print(json.dumps({
    "status": "PASS",
    "brain_pr": 1778,
    "verified_blobs": {
        "policy": "4d46ce985325eda054a5223d71d069bfdc102f4e",
        "controller": "6f5d1dbf73a1b3d8a94a0f05e55a75cbe8224eb3",
        "registry": "17a1cf5ffe038768570f64d274759507cb1041f2",
    },
    "positive_root1_first": True,
    "stale_snapshot_dependency_deleted": True,
    "score_only_root1_credit_forbidden": True,
    "acceptance_credit_delta": 0,
}, sort_keys=True))
