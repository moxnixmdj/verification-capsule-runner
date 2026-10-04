#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "canonical"

EXPECTED_BLOBS = {
    CANON / "runtime" / "terminal_stronger_proof_replacement_compiler_v1.py": "3b2f617f56df10cb1ca663effd3f58089a570d90",
    CANON / "runtime" / "precommit_isolation_guard_v1.py": "caf2b06071cfd121a27eafde651c401825fc5c81",
    CANON / "governance" / "TERMINAL_STRUCTURAL_BREAKTHROUGH_MINIMUM_ACTION_CUT_V1.json": "7cb7684c928e20c58cd3de1bac9b395548f39439",
    CANON / "governance" / "FRESH_REALITY_PRECOMMIT_ISOLATION_THEOREM_CANDIDATE_V1.json": "7b29ef43e041040736b8adc7b92a94f3d4cfec43",
}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    framed = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(framed).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


for path, expected in EXPECTED_BLOBS.items():
    actual = git_blob_sha1(path)
    assert actual == expected, (path, actual, expected)

spr = load_module(
    "spr",
    CANON / "runtime" / "terminal_stronger_proof_replacement_compiler_v1.py",
)
pig = load_module(
    "pig",
    CANON / "runtime" / "precommit_isolation_guard_v1.py",
)

cut = json.loads(
    (CANON / "governance" / "TERMINAL_STRUCTURAL_BREAKTHROUGH_MINIMUM_ACTION_CUT_V1.json").read_text()
)
theorem = json.loads(
    (CANON / "governance" / "FRESH_REALITY_PRECOMMIT_ISOLATION_THEOREM_CANDIDATE_V1.json").read_text()
)

# Governance must remain zero-credit and non-authoritative.
assert cut["exact_live_state"] == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
    "root1_positive_gaps": 0,
    "root2_only": 16,
    "root3_only": 7,
    "root2_and_root3": 3,
    "terminal": False,
}
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
assert cut["fresh_reality_authority"] is False
assert all(v == 0 for v in cut["accounting"].values())
assert {
    x["id"] for x in cut["structural_actions"]
} == {
    "STRONGER_PROOF_REPLACEMENT_RACE",
    "CONSOLIDATED_AUTHENTICATED_ACCOUNT_SWEEP",
    "PRECOMMIT_ISOLATION_THEOREM_RACE",
    "OWNER_RESULT_RACES",
}

assert theorem["candidate_theorem"]["universal_claim"] is False
assert theorem["authority"]["current_fresh_reality_block_preserved"] is True
assert theorem["authority"]["execution"] is False
assert theorem["authority"]["promotion"] is False
assert theorem["authority"]["fresh_reality"] is False
assert all(v == 0 for v in theorem["accounting"].values())

# Compiler invariants.
compiled = spr.compile_replacement_races(
    ["P1", "P1", "P2"],
    deleted_routes={"P1": ["MATCHED_EMPIRICAL_COMPARISON"]},
)
assert compiled["predicate_count"] == 2
assert compiled["acceptance_credit_authorized"] is False
assert compiled["execution_authority"] is False
assert compiled["promotion_authority"] is False
assert compiled["fresh_reality_authority"] is False
assert "MATCHED_EMPIRICAL_COMPARISON" not in {
    x["route"] for x in compiled["races"][0]["routes"]
}

base_cert = {
    "target_predicate": "P1",
    "target_contract_sha256": "a" * 64,
    "proof_kind": "FORMAL_ENTAILMENT",
    "scope_relation": "SUPERSET",
    "semantic_implication_proved": True,
    "metric_threshold_implication_proved": True,
    "independent_verification_pass": True,
    "source_content_addressed": True,
}
good = spr.check_replacement_certificate(base_cert)
assert good["replacement_certificate_mechanically_complete"] is True
assert good["acceptance_credit_authorized"] is False
assert good["requires_separate_predicate_specific_activation"] is True

for key, bad_value, expected_reason in [
    ("scope_relation", "SUBSET", "SCOPE_RELATION_MUST_BE_EXACT_OR_SUPERSET"),
    ("semantic_implication_proved", False, "SEMANTIC_IMPLICATION_NOT_PROVED"),
    ("metric_threshold_implication_proved", False, "METRIC_THRESHOLD_IMPLICATION_NOT_PROVED"),
    ("independent_verification_pass", False, "INDEPENDENT_VERIFICATION_NOT_BOUND"),
    ("source_content_addressed", False, "SOURCE_NOT_CONTENT_ADDRESSED"),
]:
    c = dict(base_cert)
    c[key] = bad_value
    out = spr.check_replacement_certificate(c)
    assert out["replacement_certificate_mechanically_complete"] is False
    assert expected_reason in out["reasons"]

c = dict(base_cert)
c["proof_kind"] = "MATCHED_EMPIRICAL_COMPARISON"
out = spr.check_replacement_certificate(c)
assert out["replacement_certificate_mechanically_complete"] is False
assert "PROOF_KIND_NOT_A_STRONGER_PROOF_ROUTE" in out["reasons"]

# Precommit isolation guard invariants.
receipt = {
    "candidate_sha256": "1" * 64,
    "harness_sha256": "2" * 64,
    "scorer_sha256": "3" * 64,
    "environment_sha256": "4" * 64,
    "policy_sha256": "5" * 64,
    "commitment_recorded_before_case_reveal": True,
    "independent_executor": True,
    "candidate_immutable_during_execution": True,
    "no_adaptive_state_channel": True,
    "outputs_bound_to_commitment": True,
    "benchmark_protocol_comparability_verified": True,
    "observed_candidate_sha256": "1" * 64,
}
receipt["commitment_sha256"] = pig.commitment_digest(receipt)
ok = pig.verify_precommit_isolation_receipt(receipt)
assert ok["mechanical_isolation_gate_pass"] is True
assert ok["fresh_reality_authority"] is False
assert ok["execution_authority"] is False
assert ok["promotion_authority"] is False
assert ok["requires_benchmark_specific_semantic_proof"] is True
assert ok["requires_independent_activation"] is True

for key, bad_value, expected_reason in [
    ("commitment_recorded_before_case_reveal", False, "COMMITMENT_NOT_PROVED_BEFORE_CASE_REVEAL"),
    ("independent_executor", False, "INDEPENDENT_EXECUTOR_NOT_PROVED"),
    ("candidate_immutable_during_execution", False, "CANDIDATE_IMMUTABILITY_NOT_PROVED"),
    ("no_adaptive_state_channel", False, "ADAPTIVE_STATE_CHANNEL_NOT_EXCLUDED"),
    ("outputs_bound_to_commitment", False, "OUTPUTS_NOT_BOUND_TO_COMMITMENT"),
    ("benchmark_protocol_comparability_verified", False, "BENCHMARK_PROTOCOL_COMPARABILITY_NOT_VERIFIED"),
    ("observed_candidate_sha256", "9" * 64, "EXECUTED_CANDIDATE_DIFFERS_FROM_COMMITTED_CANDIDATE"),
]:
    r = dict(receipt)
    r[key] = bad_value
    out = pig.verify_precommit_isolation_receipt(r)
    assert out["mechanical_isolation_gate_pass"] is False
    assert expected_reason in out["reasons"]

r = dict(receipt)
r["commitment_sha256"] = "0" * 64
out = pig.verify_precommit_isolation_receipt(r)
assert out["mechanical_isolation_gate_pass"] is False
assert "COMMITMENT_DIGEST_MISMATCH" in out["reasons"]

print(json.dumps({
    "status": "INDEPENDENT_STATIC_AND_ADVERSARIAL_PASS",
    "exact_blob_count": len(EXPECTED_BLOBS),
    "stronger_proof_fail_closed": True,
    "precommit_guard_fail_closed": True,
    "acceptance_credit_delta": 0,
    "fresh_reality_authority": False,
}, sort_keys=True))
