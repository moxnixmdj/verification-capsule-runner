from __future__ import annotations

import inspect
import json
from pathlib import Path

from canonical.runtime.tool_discovery_owned_universal_v5 import (
    OwnedToolAuthorityV5,
    apply_discovery,
    next_action,
    theorem_invariants,
)

ROOT = Path(__file__).resolve().parent
CAP = "CAP_A"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def find(obj, key, value):
    if isinstance(obj, dict):
        if obj.get(key) == value:
            return obj
        for child in obj.values():
            out = find(child, key, value)
            if out is not None:
                return out
    elif isinstance(obj, list):
        for child in obj:
            out = find(child, key, value)
            if out is not None:
                return out
    return None


def row(tid, cost, source, support, available, authorized, admissible, probe=True):
    return {
        "tool_id": tid,
        "source_id": source,
        "cost": float(cost),
        "available": bool(available),
        "authorized": bool(authorized),
        "admissible": bool(admissible),
        "safe_probe_capabilities": [CAP] if probe else [],
        "capabilities": [CAP] if support else [],
        "opaque_schema": "schema-" + tid,
    }


def execute(entries, *, prior=()):
    authority = OwnedToolAuthorityV5(entries)
    public = authority.initial_public(required_capabilities=[CAP], prior_probe_receipts=prior)
    assert public["visible_tools"] == []
    actions = []
    for _ in range(100):
        action = next_action(public)
        actions.append(dict(action))
        kind = action["action"]
        if kind == "DISCOVER":
            receipt = authority.discover(action["source_id"], episode_epoch=public["authority_epoch"])
            apply_discovery(public, receipt)
            continue
        if kind == "PROBE":
            public["prior_probe_receipts"].append(
                authority.safe_probe(
                    action["tool_id"],
                    action["capability"],
                    episode_epoch=public["authority_epoch"],
                )
            )
            continue
        if kind in {"SELECT", "ESCALATE"}:
            return action, public, actions
        raise AssertionError(action)
    raise AssertionError("ACTION_BUDGET_EXHAUSTED")


def target_preservation_checks():
    protocols = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    registry = load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    binding = load("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
    evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    theorem = load("canonical/governance/TOOL_DISCOVERY_OWNED_UNIVERSAL_V5_THEOREM_V1.json")
    intent = load("canonical/action_intents/2026-10-03_TOOL_DISCOVERY_OWNED_UNIVERSAL_V5_V1.json")

    fam = find(protocols, "family", "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    beh = find(registry, "behavior_id", "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
    assert fam is not None and beh is not None

    required_dims = {
        "unknown tool discovery",
        "schema/authority filtering",
        "route selection under incomplete evidence",
        "safe probe choice",
        "capability-state update",
        "later-task transfer without rediscovery",
    }
    assert required_dims <= set(fam["task_dimensions"])
    assert "Opus matched bounds" in fam["acceptance"]
    assert "available tool schemas/capabilities" in beh["inputs"]
    assert "unknown or changing capabilities" in beh["environment_state"]
    assert "Discover candidate tools if needed" in beh["required_output_or_action"]
    assert beh["scope"] == "Unknown/changing tool ecosystem to verified usable route"

    dims = set(binding["objective_dimensions"])
    assert {
        "UNKNOWN_CAPABILITY_DISCOVERY",
        "ACTIVE_CONSTRAINT_ADMISSIBILITY",
        "LEAST_COST_SUFFICIENT_ROUTE",
        "SAFE_RELEVANT_PROBE_SELECTION",
        "EVIDENCE_BACKED_CAPABILITY_UPDATE",
        "CROSS_TASK_TRANSFER",
        "VERSION_STALENESS_INVALIDATION",
        "KNOWN_UNSUITABLE_PROBE_SUPPRESSION",
        "CORRECT_NO_ROUTE_ESCALATION",
    } <= dims
    visible = set(binding["information_boundary"]["candidate_visible"])
    hidden = set(binding["information_boundary"]["hidden_from_candidate"])
    assert "SAFE_PROBE_PERMISSION" in visible
    assert "ACTUAL_TOOL_CAPABILITY_MATRIX" in hidden

    transfer = find(evidence, "predicate_id", "TOOL_LEARNING_SECOND_TASK_TRANSFER")
    unsupported = find(evidence, "predicate_id", "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION")
    success = find(evidence, "predicate_id", "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
    assert transfer["state"] == "PROVED"
    assert unsupported["state"] == "PROVED"
    assert success["state"] != "PROVED"

    assert theorem["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert theorem["capability_credit_delta"] == 0
    assert theorem["family_credit_delta"] == 0
    assert theorem["execution_authority"] is False
    assert theorem["promotion_authority"] is False
    assert "NO_REINTERPRETATION_OF_UNKNOWN_TOOL_DISCOVERY_AS_VISIBLE_IDENTITIES_ONLY" in theorem["hard_nonclaims"]
    assert intent["blocker_id"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert intent["new_reality_units_consumed"] == 0


def structural_information_safety_checks():
    import canonical.runtime.tool_discovery_owned_universal_v5 as runtime

    digest_src = inspect.getsource(runtime.OwnedToolAuthorityV5.registry_digest_sha256)
    assert "capabilities" not in digest_src, digest_src

    policy_src = inspect.getsource(runtime.next_action)
    assert policy_src.index("if sources:") < policy_src.index("evidence = _evidence(public)")
    assert 't.get("admissible") is True' in policy_src
    assert "SAFE_PROBE_PERMISSION_MISSING_FOR_UNRESOLVED_CHEAPER_ROUTE" in policy_src

    yes = OwnedToolAuthorityV5([
        row("x", 1, "S0", True, True, True, True)
    ], epoch=4)
    no = OwnedToolAuthorityV5([
        row("x", 1, "S0", False, True, True, True)
    ], epoch=4)
    assert yes.registry_digest_sha256() == no.registry_digest_sha256()
    assert yes.discover("S0", episode_epoch=4) == no.discover("S0", episode_epoch=4)

    inv = theorem_invariants(yes)
    assert inv["source_union_exact_registry"] is True
    assert inv["hidden_capabilities_absent_from_discovery"] is True


def independent_exhaustive_oracle():
    # 4 tools and four independent binary dimensions:
    # support, availability, authorization, normalized active-constraint admissibility.
    # 16^4 = 65,536 complete worlds. Identities begin hidden in every world.
    tids = ["T0", "T1", "T2", "T3"]
    costs = [1.0, 2.0, 3.0, 4.0]
    checked = 0
    for support_mask in range(16):
        for availability_mask in range(16):
            for authorization_mask in range(16):
                for admissible_mask in range(16):
                    entries = []
                    for i, tid in enumerate(tids):
                        entries.append(row(
                            tid,
                            costs[i],
                            "S" + str(i % 3),
                            bool(support_mask & (1 << i)),
                            bool(availability_mask & (1 << i)),
                            bool(authorization_mask & (1 << i)),
                            bool(admissible_mask & (1 << i)),
                        ))
                    final, public, actions = execute(entries)
                    expected_rows = [
                        x for x in entries
                        if x["available"] and x["authorized"] and x["admissible"]
                        and CAP in x["capabilities"]
                    ]
                    expected = min(expected_rows, key=lambda x: (x["cost"], x["tool_id"]))["tool_id"] if expected_rows else None

                    # No route decision is allowed before all three sources are exhausted.
                    decision_index = next(i for i, a in enumerate(actions) if a["action"] in {"PROBE", "SELECT", "ESCALATE"})
                    assert sum(1 for a in actions[:decision_index] if a["action"] == "DISCOVER") == 3

                    if expected is None:
                        assert final["action"] == "ESCALATE", (support_mask, availability_mask, authorization_mask, admissible_mask, final)
                        assert final["reason"] == "NO_VERIFIED_ADMISSIBLE_SUFFICIENT_ROUTE", final
                    else:
                        assert final == {"action": "SELECT", "tool_id": expected}, (support_mask, availability_mask, authorization_mask, admissible_mask, final)
                    checked += 1
    assert checked == 65536
    return checked


def permission_fail_closed_check():
    entries = [
        row("cheap", 1, "S0", True, True, True, True, probe=False),
        row("expensive", 10, "S1", True, True, True, True, probe=True),
    ]
    final, _, _ = execute(entries)
    assert final["action"] == "ESCALATE"
    assert final["reason"] == "SAFE_PROBE_PERMISSION_MISSING_FOR_UNRESOLVED_CHEAPER_ROUTE"
    assert final["tool_id"] == "cheap"


def main():
    target_preservation_checks()
    structural_information_safety_checks()
    checked = independent_exhaustive_oracle()
    permission_fail_closed_check()
    print(json.dumps({
        "status": "INDEPENDENT_PASS__TOOL_DISCOVERY_OWNED_UNIVERSAL_V5_CANDIDATE",
        "brain_pr": 1160,
        "exhaustive_worlds_checked": checked,
        "target_preservation": True,
        "unknown_identities_start_hidden": True,
        "discovery_before_route_decision": True,
        "active_constraint_admissibility_load_bearing": True,
        "hidden_state_digest_noninterference": True,
        "missing_probe_permission_fails_closed": True,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_granted": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
