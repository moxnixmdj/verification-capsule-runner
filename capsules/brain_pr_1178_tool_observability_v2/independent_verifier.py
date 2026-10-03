from __future__ import annotations

import itertools
import json
import pathlib

from canonical.runtime.tool_discovery_observability_partition_v2 import classify

SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
UNKNOWN = "UNKNOWN"


def tool(tid, cost, state, safe):
    return {
        "tool_id": tid,
        "cost": cost,
        "capability_evidence": {"A": state},
        "safe_probe_capabilities": ["A"] if safe else [],
    }


def payload(*rows):
    return {
        "identity_scope_complete": True,
        "required_capabilities": ["A"],
        "admissible_tools": list(rows),
    }


def oracle(rows):
    verified = [r for r in rows if r["state"] == SUPPORTED]
    best = min((r["cost"] for r in verified), default=None)
    unresolved = [
        r for r in rows
        if r["state"] == UNKNOWN and (best is None or r["cost"] < best)
    ]
    if not unresolved:
        return "UNIVERSAL_PROOF"
    frontier = min(r["cost"] for r in unresolved)
    at_frontier = [r for r in unresolved if r["cost"] == frontier]
    if any(r["safe"] for r in at_frontier):
        return "SAFE_PROBE"
    return "MATCHED_COMPARATOR"


def exhaustive_two_tool_oracle():
    states = [SUPPORTED, UNSUPPORTED, UNKNOWN]
    cost_pairs = [(1, 1), (1, 2), (2, 1), (2, 2)]
    checked = 0
    for s0, s1, safe0, safe1, costs in itertools.product(
        states, states, [False, True], [False, True], cost_pairs
    ):
        rows = [
            {"id": "T0", "cost": costs[0], "state": s0, "safe": safe0},
            {"id": "T1", "cost": costs[1], "state": s1, "safe": safe1},
        ]
        expected = oracle(rows)
        out = classify(payload(
            tool("T0", costs[0], s0, safe0),
            tool("T1", costs[1], s1, safe1),
        ))
        got = out["minimum_reality_action"]
        assert got == expected, (rows, expected, out)
        checked += 1
    return checked


def multi_capability_attacks():
    # Unsafe A coexists with safe B on the cheapest frontier. Comparator is
    # premature because B=false would eliminate the entire route.
    mixed = {
        "identity_scope_complete": True,
        "required_capabilities": ["A", "B"],
        "admissible_tools": [
            {
                "tool_id": "CHEAP",
                "cost": 1,
                "capability_evidence": {"A": "UNKNOWN", "B": "UNKNOWN"},
                "safe_probe_capabilities": ["B"],
            },
            {
                "tool_id": "KNOWN",
                "cost": 2,
                "capability_evidence": {"A": "SUPPORTED", "B": "SUPPORTED"},
                "safe_probe_capabilities": ["A", "B"],
            },
        ],
    }
    out = classify(mixed)
    assert out["minimum_reality_action"] == "SAFE_PROBE", out
    assert out["recommended_safe_probe"] == {
        "tool_id": "CHEAP",
        "capability": "B",
        "reason": (
            "CHEAPEST_UNRESOLVED_FRONTIER_HAS_SAFE_DECIDABLE_FACT__"
            "RESULT_CAN_ELIMINATE_OR_ADVANCE_ROUTE_BEFORE_COMPARATOR_SPEND"
        ),
    }, out

    # Negative B deletes the route, so the hidden A fact ceases to matter.
    neg = json.loads(json.dumps(mixed))
    neg["admissible_tools"][0]["capability_evidence"]["B"] = "UNSUPPORTED"
    out = classify(neg)
    assert out["minimum_reality_action"] == "UNIVERSAL_PROOF", out

    # Positive B leaves A as the only unresolved cheapest-frontier fact.
    pos = json.loads(json.dumps(mixed))
    pos["admissible_tools"][0]["capability_evidence"]["B"] = "SUPPORTED"
    out = classify(pos)
    assert out["minimum_reality_action"] == "MATCHED_COMPARATOR", out
    assert out["irreducible_routes"][0]["unsafe_unknown_capabilities"] == ["A"], out


def tie_attack():
    # Equal-cost identity is not load-bearing for a least-cost objective.
    out = classify(payload(
        tool("KNOWN", 1, SUPPORTED, False),
        tool("UNKNOWN_TIE", 1, UNKNOWN, False),
    ))
    assert out["minimum_reality_action"] == "UNIVERSAL_PROOF", out
    assert out["best_verified_sufficient_cost"] == 1.0, out


def fail_closed_and_zero_credit():
    bad = payload(tool("T", 1, SUPPORTED, False))
    bad["identity_scope_complete"] = False
    out = classify(bad)
    assert out["status"] == "FAIL_CLOSED__INVALID_PARTITION_INPUT", out
    assert out["matched_comparator_required_now"] is True, out

    gov = json.loads(pathlib.Path(
        "canonical/governance/TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V2.json"
    ).read_text())
    intent = json.loads(pathlib.Path(
        "canonical/action_intents/2026-10-03_TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V2.json"
    ).read_text())
    for obj in (gov, intent):
        assert obj["new_reality_units_consumed"] == 0
        assert obj["capability_credit_delta"] == 0
        assert obj["family_credit_delta"] == 0
        assert obj["execution_authority"] is False
        assert obj["promotion_authority"] is False


def source_semantic_guards():
    src = pathlib.Path(
        "canonical/runtime/tool_discovery_observability_partition_v2.py"
    ).read_text()
    # Strict inequality is load-bearing. If this silently drifts to <=, the
    # equal-cost attack above must fail.
    assert 'row["cost"] < best_verified_cost' in src
    assert "SAFE_OBSERVATION_CLOSURE_PRECEDES_MATCHED_COMPARATOR_SPEND" in pathlib.Path(
        "canonical/governance/TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V2.json"
    ).read_text()


def main():
    checked = exhaustive_two_tool_oracle()
    multi_capability_attacks()
    tie_attack()
    fail_closed_and_zero_credit()
    source_semantic_guards()
    print(json.dumps({
        "status": "PASS__INDEPENDENT_OBSERVABILITY_PARTITION_V2",
        "exhaustive_two_tool_worlds": checked,
        "mixed_safe_unsafe_attack": "PASS",
        "equal_cost_attack": "PASS",
        "fail_closed": "PASS",
        "credit_delta": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
