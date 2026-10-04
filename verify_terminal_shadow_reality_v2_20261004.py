#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "terminal_shadow_reality_v2_20261004"
RUNTIME = SUBJECT / "canonical" / "runtime" / "terminal_state_compression_scheduler_v1.py"
DEPENDENCY = SUBJECT / "canonical" / "runtime" / "generic_precommit_isolation_theorem_v1.py"
POLICY = SUBJECT / "PROOF_CARRYING_SHADOW_REALITY_POLICY_V2.json"

EXPECTED_RUNTIME_BLOB = "fd5639e9d503f59913bfbd08e47799ef5132b1e7"
EXPECTED_DEPENDENCY_BLOB = "58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296"
EXPECTED_POLICY_BLOB = "756a608f0a3acaa72e56abbaa078f1cf0f3df938"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


assert git_blob_sha(RUNTIME) == EXPECTED_RUNTIME_BLOB
assert git_blob_sha(DEPENDENCY) == EXPECTED_DEPENDENCY_BLOB
assert git_blob_sha(POLICY) == EXPECTED_POLICY_BLOB

sys.path.insert(0, str(SUBJECT))
m = importlib.import_module("canonical.runtime.terminal_state_compression_scheduler_v1")
g = importlib.import_module("canonical.runtime.generic_precommit_isolation_theorem_v1")

policy = json.loads(POLICY.read_text())
assert policy["authority"]["shadow_collection"] is False
assert policy["authority"]["terminal_execution"] is False
assert policy["authority"]["promotion"] is False
assert policy["authority"]["fresh_reality_promotion"] is False
assert policy["accounting"]["acceptance_credit_delta"] == 0
assert policy["accounting"]["new_reality_units_consumed"] == 0


def isolation_receipt():
    r = {}
    for i, c in enumerate(("candidate", "harness", "scorer", "environment", "policy"), start=1):
        r[f"{c}_sha256"] = str(i) * 64
        r[f"observed_{c}_sha256"] = str(i) * 64
    r.update({
        "commit_event_sequence": 10,
        "case_reveal_event_sequence": 11,
        "execution_start_event_sequence": 12,
        "independent_executor": True,
        "committed_components_immutable": True,
        "no_case_or_evaluation_feedback_to_committed_components": True,
        "unrelated_work_cannot_mutate_committed_components": True,
        "outputs_bound_to_commitment": True,
        "observed_causal_edges": [
            ["case_content", "execution_output"],
            ["evaluation_output", "receipt_store"],
        ],
    })
    r["commitment_sha256"] = g.commitment_digest(r)
    return r


def adapter():
    return {
        "population_identity_verified": True,
        "scorer_or_grader_equivalence_verified": True,
        "effort_and_context_semantics_verified": True,
        "tool_and_environment_boundary_verified": True,
        "exact_comparator_identity_verified": True,
        "no_proxy_substitution_verified": True,
        "zero_incremental_spend_or_entitlement_verified": True,
        "acceptance_rule_bound": True,
    }


def lease():
    return {
        "isolation_receipt": isolation_receipt(),
        "benchmark_adapter": adapter(),
        "candidate_frozen": True,
        "outputs_bound_to_precommit": True,
        "outputs_escrowed": True,
        "outputs_hidden_from_candidate": True,
        "outputs_hidden_from_optimizer_until_release": True,
        "outputs_hidden_from_candidate_mutators_until_release": True,
        "unrelated_work_cannot_mutate_candidate": True,
        "zero_incremental_spend_guard": True,
        "route_result_not_used_for_acceptance_before_fixed_point": True,
        "release_requires_zero_reality_fixed_point": True,
        "release_requires_independent_verification": True,
        "one_use_lease": True,
        "shadow_authority_receipt_content_addressed": True,
        "explicit_shadow_reality_authority": True,
        "shadow_authority_receipt_sha256": "a" * 64,
        "lease_nonce_sha256": "b" * 64,
        "lease_id": "shadow:test:v2",
        "benchmark_id": "LIVEBENCH_IF_GE_65_7",
        "escrow_sink_id": "escrow:test:v2",
        "lease_consumed": False,
        "execution_ordinal": 0,
        "acceptance_credit_before_fixed_point": False,
        "promotion_before_fixed_point": False,
        "candidate_can_read_shadow_outputs": False,
        "optimizer_can_read_shadow_outputs_before_release": False,
    }


# Positive lease: collection-ready, still zero promotion/release authority.
base = lease()
out = m.verify_shadow_reality_lease(base)
assert out["shadow_collection_ready"] is True
assert out["generic_isolation_kernel_pass"] is True
assert out["benchmark_thin_adapter_pass"] is True
assert out["shadow_collection_authority_granted_by_this_module"] is False
assert out["acceptance_credit_authorized"] is False
assert out["promotion_authority"] is False
assert out["fresh_reality_promotion_authority"] is False

# A self-asserted boolean cannot replace the actual underlying isolation receipt.
bad = lease()
bad.pop("isolation_receipt")
bad["generic_isolation_kernel_pass"] = True
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "MISSING_ISOLATION_RECEIPT" in out["reasons"]

# Hash drift must be caught by re-running the generic verifier.
bad = lease()
bad["isolation_receipt"]["observed_harness_sha256"] = "9" * 64
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "GENERIC_ISOLATION_KERNEL_FAIL" in out["reasons"]

# Thin-adapter failure must fail closed.
bad = lease()
bad["benchmark_adapter"]["exact_comparator_identity_verified"] = False
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "BENCHMARK_THIN_ADAPTER_FAIL" in out["reasons"]

# Authority cannot be self-created by the runtime.
bad = lease()
bad["explicit_shadow_reality_authority"] = False
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "EXPLICIT_SHADOW_REALITY_AUTHORITY_MISSING" in out["reasons"]

# Result leakage to optimizer or candidate blocks collection.
bad = lease()
bad["optimizer_can_read_shadow_outputs_before_release"] = True
assert m.verify_shadow_reality_lease(bad)["shadow_collection_ready"] is False
bad = lease()
bad["candidate_can_read_shadow_outputs"] = True
assert m.verify_shadow_reality_lease(bad)["shadow_collection_ready"] is False

# Replay protection and zero-spend result escrow.
result = {
    "lease_id": base["lease_id"],
    "execution_count": 1,
    "lease_consumed_after_execution": True,
    "result_content_addressed": True,
    "result_sha256": "c" * 64,
    "result_escrowed": True,
    "result_visible_to_candidate": False,
    "result_visible_to_optimizer": False,
    "incremental_spend_usd": 0,
    "acceptance_credit_delta": 0,
    "promotion_performed": False,
}
r = m.verify_shadow_execution_result(base, result)
assert r["shadow_result_escrow_valid"] is True
assert r["score_release_authorized"] is False
assert r["acceptance_credit_authorized"] is False

bad_result = dict(result)
bad_result["execution_count"] = 2
assert m.verify_shadow_execution_result(base, bad_result)["shadow_result_escrow_valid"] is False

bad_result = dict(result)
bad_result["incremental_spend_usd"] = 0.01
assert m.verify_shadow_execution_result(base, bad_result)["shadow_result_escrow_valid"] is False

bad_result = dict(result)
bad_result["result_visible_to_optimizer"] = True
assert m.verify_shadow_execution_result(base, bad_result)["shadow_result_escrow_valid"] is False

# Probability semantics and state-compression ranking.
assert m.classify_probability_state() == "UNKNOWN__NO_POINT_ESTIMATE"
assert m.classify_probability_state(deterministic_entailment=True) == "ONE"
assert m.classify_probability_state(falsified_until_wake=True) == "ZERO_UNTIL_MATERIAL_WAKE"

score = m.robust_state_compression_priority(
    guaranteed_progress=0,
    guaranteed_deletion=1,
    guaranteed_information=1,
    critical_path_seconds=2,
)
assert score == 1.0

bound = m.makespan_bound(120, 80)
assert bound["serial_seconds"] == 200
assert bound["overlapped_seconds"] == 120
assert bound["maximum_structural_seconds_saved"] == 80
assert bound["structural_speedup_upper_bound"] == 200 / 120

print("PASS: terminal shadow reality V2 is fail-closed, dependency-pinned, replay-safe, and zero-credit")
