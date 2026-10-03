from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from canonical.runtime import acceptance_proof_transmuter_v1 as transmuter

ROOT = Path(__file__).resolve().parent
FAMILY = "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
PREDICATE = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"

PATHS = {
    "transmuter": "canonical/runtime/acceptance_proof_transmuter_v1.py",
    "protocols": "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
    "witness": "canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json",
    "scope": "canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "input": "canonical/governance/OPUS55_TOOL_DISCOVERY_SCOPE_COMPLETE_ACCEPTANCE_INPUT_V1.json",
}
EXPECTED = {
    PATHS["transmuter"]: "39b5611e53485674b29e2a05da91b89801bc5aa6",
    PATHS["protocols"]: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    PATHS["witness"]: "60a7c1139cad315d977bf5ed97e708cc5ec3fcc7",
    PATHS["scope"]: "c9adf25c2e63f9e8b111f1d022acda264d6571f5",
    PATHS["input"]: "4c7d170418bb95828a23538709aa304a00db6746",
}

def blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(rel: str) -> dict:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(value, dict), rel
    return value

def scope_admissible(scope: dict) -> bool:
    return all([
        str(scope.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        scope.get("target_family") == FAMILY,
        scope.get("target_predicate") == PREDICATE,
        scope.get("basis_kind") == "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        scope.get("proof_domain") == "EXACT_FROZEN_TOOL_DISCOVERY_TERMINAL_TARGET_ONLY",
        scope.get("scope_semantics_discharged") is True,
        scope.get("complete_target_case_set") is True,
        scope.get("public_runner", {}).get("conclusion") == "success",
        scope.get("terminal_cases_replayed") == 0,
        scope.get("new_reality_units_consumed") == 0,
        scope.get("capability_credit_delta") == 0,
        scope.get("family_credit_delta") == 0,
        scope.get("execution_authority") is False,
        scope.get("promotion_authority") is False,
    ])

def tool_row(compiled: dict) -> dict:
    return next(x for x in compiled["families"] if x["family"] == FAMILY)

def assert_only_tool_delta(compiled: dict, protocols: dict) -> None:
    assert compiled["status"] == "PASS", compiled
    assert compiled["family_count"] == 19, compiled
    assert compiled["closed_family_count"] == 4, compiled
    assert compiled["open_family_count"] == 15, compiled
    expected_prior = {
        "EXACT_SYMBOLIC_COMPUTATION",
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
        "SUBAGENT_DELEGATION_AND_COORDINATION",
    }
    pass_rows = {x["family"] for x in compiled["families"] if x["result_status"] == "PASS"}
    assert pass_rows == expected_prior | {FAMILY}, pass_rows
    for p in protocols["protocols"]:
        row = next(x for x in compiled["families"] if x["family"] == p["family"])
        if p["family"] in expected_prior:
            assert p["status"] == "PASS", p
            assert row["result_status"] == "PASS" and row["closure_mode"] == "ALREADY_PASS", row
        elif p["family"] == FAMILY:
            assert p["status"] == "DEFINED_RESULT_OPEN", p
            assert row["result_status"] == "PASS", row
            assert row["closure_mode"] == "ABSOLUTE_DOMINANCE", row
            assert row["witness_reason"] == "THEORETICAL_CEILING_DOMINANCE", row
        else:
            assert p["status"] != "PASS", p
            assert row["result_status"] == "DEFINED_RESULT_OPEN", row
    assert compiled["capability_credit_delta"] == 0
    assert compiled["family_credit_delta"] == 0
    assert compiled["execution_authority"] is False
    assert compiled["promotion_authority"] is False

def main() -> int:
    actual = {p: blob(p) for p in EXPECTED}
    assert actual == EXPECTED, {"actual": actual, "expected": EXPECTED}

    protocols = load(PATHS["protocols"])
    witness = load(PATHS["witness"])
    scope = load(PATHS["scope"])
    inp = load(PATHS["input"])

    assert scope_admissible(scope), scope
    mutated_scope = copy.deepcopy(scope)
    mutated_scope["complete_target_case_set"] = False
    assert not scope_admissible(mutated_scope)

    assert inp["protocols"] == {"path": PATHS["protocols"], "git_blob_sha": EXPECTED[PATHS["protocols"]]}
    assert inp["transmuter"] == {"path": PATHS["transmuter"], "git_blob_sha": EXPECTED[PATHS["transmuter"]]}
    assert inp["source_witness"] == {"path": PATHS["witness"], "git_blob_sha": EXPECTED[PATHS["witness"]]}
    assert inp["scope_completeness_receipt"] == PATHS["scope"]
    assert inp["new_reality_units_consumed"] == 0
    assert inp["terminal_results_replayed"] == 0
    assert inp["capability_credit_delta"] == 0 and inp["family_credit_delta"] == 0
    assert inp["execution_authority"] is False and inp["promotion_authority"] is False

    assert witness["family"] == FAMILY
    assert witness["mode"] == "ABSOLUTE_DOMINANCE"
    assert witness["verified"] is True and witness["independent"] is True
    assert witness["contamination_clean"] is True and witness["binds_frozen_protocol"] is True
    assert witness["closes_entire_protocol"] is True
    assert witness["scope_relation"] == "PROVEN_STRONGER"
    assert witness["source_case_count"] == 180
    assert witness["result"] == {"direction": "higher", "brain_lower_bound": 1, "theoretical_upper_bound": 1}

    evidence = inp["evidence"]
    assert isinstance(evidence, list) and len(evidence) == 1
    e = evidence[0]
    for key in (
        "family", "mode", "verified", "independent", "contamination_clean",
        "binds_frozen_protocol", "scope_relation", "closes_entire_protocol",
        "source_behavior_id", "source_terminal_full_result_sha256", "source_case_count", "result",
    ):
        assert e[key] == witness[key], (key, e.get(key), witness.get(key))
    assert e["scope_completeness"] == {
        "verified": True,
        "independent": True,
        "basis": "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "complete_target_case_set": True,
        "receipt": PATHS["scope"],
    }

    compiled = transmuter.evaluate(protocols, inp)
    assert_only_tool_delta(compiled, protocols)

    for mutator in (
        lambda x: x["evidence"][0]["scope_completeness"].__setitem__("verified", False),
        lambda x: x["evidence"][0]["result"].__setitem__("brain_lower_bound", 0.99),
        lambda x: x["evidence"][0].__setitem__("closes_entire_protocol", False),
    ):
        bad = copy.deepcopy(inp)
        mutator(bad)
        out = transmuter.evaluate(protocols, bad)
        assert out["closed_family_count"] == 3, out
        assert tool_row(out)["result_status"] == "DEFINED_RESULT_OPEN", out

    verdict = {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_CURRENT_CANONICAL_ACCEPTANCE_PUBLIC_VERIFIER_V1",
        "status": "PASS__CURRENT_CANONICAL_BYTES__TOOL_DISCOVERY_ONLY_CLOSES__4_OF_19__ZERO_REALITY",
        "family": FAMILY,
        "predicate": PREDICATE,
        "family_count": 19,
        "closed_family_count": 4,
        "open_family_count": 15,
        "newly_closed_families": [FAMILY],
        "closure_mode": "ABSOLUTE_DOMINANCE",
        "witness_reason": "THEORETICAL_CEILING_DOMINANCE",
        "scope_basis": "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "source_blobs": actual,
        "terminal_goal_achieved": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
