from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parent
EXPECTED_BLOB = "f019b28366b985dec2d6e3dec527e54482d9af3b"
SOURCE_REL = Path("brain") / "canonical/governance/OPUS55_CONFIGURABLE_CAPABILITY_QUANTIFIER_CORRECTION_20261005_V1.json"

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()

def load_source() -> dict:
    data = (ROOT / SOURCE_REL).read_bytes()
    actual = git_blob_sha(data)
    if actual != EXPECTED_BLOB:
        raise AssertionError(("SOURCE_BLOB_MISMATCH", actual, EXPECTED_BLOB))
    return json.loads(data)

def validate_reward(reward: Sequence[float]) -> tuple[float, ...]:
    if not reward:
        raise ValueError("EMPTY_REWARD")
    vals = tuple(float(x) for x in reward)
    if any(x < 0.0 or x > 1.0 for x in vals):
        raise ValueError("REWARD_OUT_OF_BOUNDS")
    return vals

def validate_distribution(dist: Sequence[float], n: int) -> tuple[float, ...]:
    vals = tuple(float(x) for x in dist)
    if len(vals) != n:
        raise ValueError("DISTRIBUTION_ARITY_MISMATCH")
    if any(x < 0.0 for x in vals):
        raise ValueError("NEGATIVE_PROBABILITY")
    if abs(sum(vals) - 1.0) > 1e-12:
        raise ValueError("DISTRIBUTION_NOT_NORMALIZED")
    return vals

def target_expected(reward: Sequence[float], dist: Sequence[float]) -> float:
    r = validate_reward(reward)
    p = validate_distribution(dist, len(r))
    return sum(pi * ri for pi, ri in zip(p, r))

def task_conditioned_argmax(reward: Sequence[float]) -> int:
    r = validate_reward(reward)
    return max(range(len(r)), key=lambda i: r[i])

def convex_dominance_witness(reward: Sequence[float], target_distributions: Iterable[Sequence[float]]) -> dict:
    r = validate_reward(reward)
    action = task_conditioned_argmax(r)
    brain_value = r[action]
    targets = [target_expected(r, d) for d in target_distributions]
    if any(v > brain_value + 1e-12 for v in targets):
        raise AssertionError("CONVEX_UPPER_BOUND_VIOLATED")
    return {
        "action": action,
        "brain_value": brain_value,
        "target_values": targets,
        "proof_rule": "EXPECTED_REWARD_IS_A_CONVEX_COMBINATION_AND_CANNOT_EXCEED_MAX_REWARD",
    }

def certify_explicit_exact_task(
    reward: Sequence[float],
    *,
    evaluator_admissibly_available: bool,
    exact_optimization_terminating: bool,
    resource_valid: bool,
    optimizer_brain_owned: bool,
) -> dict:
    guards = {
        "evaluator_admissibly_available": evaluator_admissibly_available,
        "exact_optimization_terminating": exact_optimization_terminating,
        "resource_valid": resource_valid,
        "optimizer_brain_owned": optimizer_brain_owned,
    }
    failed = [k for k, v in guards.items() if v is not True]
    if failed:
        return {
            "status": "FAIL_CLOSED",
            "failed_guards": failed,
            "dominance_authorized": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    r = validate_reward(reward)
    action = task_conditioned_argmax(r)
    return {
        "status": "PASS_EXPLICIT_EXACT_TASK_STRATUM",
        "failed_guards": [],
        "dominance_authorized": True,
        "action": action,
        "brain_value": r[action],
        "theoretical_upper_bound": max(r),
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }

def no_single_deterministic_action_maximizes_all(rewards: Sequence[Sequence[float]]) -> bool:
    rs = [validate_reward(r) for r in rewards]
    n = len(rs[0])
    if any(len(r) != n for r in rs):
        raise ValueError("REWARD_ARITY_MISMATCH")
    common = set(range(n))
    for r in rs:
        m = max(r)
        common &= {i for i, x in enumerate(r) if abs(x - m) <= 1e-12}
    return not common

def independently_verify() -> dict:
    src = load_source()

    assert src["quantifier_correction"]["fixed_policy_theorem_remains_true"] is True
    assert "FOR_ALL_TASKS_TAU__THERE_EXISTS_B_TAU" in src["definitions"]["CONFIGURABLE_CAPABILITY_CLAIM"]
    assert src["accounting"]["acceptance_credit_delta"] == 0
    assert src["fresh_reality_authority"] is False

    one_hot = [(1,0,0), (0,1,0), (0,0,1)]
    assert no_single_deterministic_action_maximizes_all(one_hot)

    target_families = [
        [(1,0,0), (0,1,0), (0,0,1), (1/3,1/3,1/3)],
        [(0.7,0.2,0.1), (0.1,0.8,0.1), (0.2,0.2,0.6)],
        [(0.25,0.25,0.5), (0.9,0.05,0.05), (0.05,0.05,0.9)],
    ]
    witnesses = []
    for r, dists in zip(one_hot, target_families):
        w = convex_dominance_witness(r, dists)
        assert w["brain_value"] == 1.0
        assert all(v <= 1.0 + 1e-12 for v in w["target_values"])
        witnesses.append(w)

    hidden = certify_explicit_exact_task(
        (0.1,0.9),
        evaluator_admissibly_available=False,
        exact_optimization_terminating=True,
        resource_valid=True,
        optimizer_brain_owned=True,
    )
    assert hidden["dominance_authorized"] is False
    assert "evaluator_admissibly_available" in hidden["failed_guards"]

    resource = certify_explicit_exact_task(
        (0.1,0.9),
        evaluator_admissibly_available=True,
        exact_optimization_terminating=True,
        resource_valid=False,
        optimizer_brain_owned=True,
    )
    assert resource["dominance_authorized"] is False

    ownership = certify_explicit_exact_task(
        (0.1,0.9),
        evaluator_admissibly_available=True,
        exact_optimization_terminating=True,
        resource_valid=True,
        optimizer_brain_owned=False,
    )
    assert ownership["dominance_authorized"] is False

    admitted = certify_explicit_exact_task(
        (0.1,0.9),
        evaluator_admissibly_available=True,
        exact_optimization_terminating=True,
        resource_valid=True,
        optimizer_brain_owned=True,
    )
    assert admitted["dominance_authorized"] is True
    assert admitted["brain_value"] == admitted["theoretical_upper_bound"]

    return {
        "schema": "PROJECT_BRAIN_CONFIGURABLE_DOMINANCE_QUANTIFIER_INDEPENDENT_VERIFICATION_V1",
        "status": "INDEPENDENT_RECOMPUTATION_PASS__QUANTIFIER_CORRECTION_AND_COUNTERMODEL_HOLD__STRICT_GUARDS_HOLD__ZERO_CREDIT",
        "source_git_blob_sha": EXPECTED_BLOB,
        "verified": [
            "FIXED_POLICY_THEOREM_NOT_REJECTED",
            "FORALL_TASK_EXISTS_CONFIG_NOT_EQUIVALENT_TO_EXISTS_CONFIG_FORALL_TASK",
            "TASK_CONDITIONED_ARGMAX_DOMINATES_ANY_TARGET_DISTRIBUTION_ON_EXPLICIT_FINITE_REWARD_STRATUM",
            "HIDDEN_EVALUATOR_FAILS_CLOSED",
            "RESOURCE_INVALID_ROUTE_FAILS_CLOSED",
            "NONOWNED_OPTIMIZER_FAILS_CLOSED",
        ],
        "witnesses": witnesses,
        "hard_nonclaims": [
            "NO_ROUTE_C_GLOBAL_COVERAGE_PROOF",
            "NO_ATOMIC_ACCEPTANCE_CREDIT",
            "NO_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_FRESH_REALITY_AUTHORITY",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }

if __name__ == "__main__":
    print(json.dumps(independently_verify(), indent=2, sort_keys=True))
