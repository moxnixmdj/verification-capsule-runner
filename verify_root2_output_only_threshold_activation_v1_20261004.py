from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "root2_output_only_threshold_activation_v1_20261004"
ACT = SUB / "ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1.json"
ROOT_STATE = SUB / "TERMINAL_ROOT_CAUSE_STATE_V1.json"

EXPECTED_ACTIVATION_BLOB = "7ea4dd4edb59c8526bd3993e02f4a8fb53c65085"
EXPECTED_ROOT_BLOB = "601e82d00104b4ed36ee5968ad966a0c02e627c1"
EXPECTED_MANIFEST_BLOB = "1fba51d15bcfdf6accd90948155517f7c9b98bbb"
EXPECTED_RUNTIME_BLOB = "7a0c715d931dbba05bc9e5ae344e1ead787ea5b8"
EXPECTED_SUBJECT_VERIFICATION_BLOB = "553602570334f39003708e52d781b8c59f27eb7c"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


assert git_blob_sha(ACT) == EXPECTED_ACTIVATION_BLOB
assert git_blob_sha(ROOT_STATE) == EXPECTED_ROOT_BLOB

activation = json.loads(ACT.read_text())
root = json.loads(ROOT_STATE.read_text())

assert activation["schema"] == "PROJECT_BRAIN_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1"
assert activation["subject"]["manifest_git_blob_sha"] == EXPECTED_MANIFEST_BLOB
assert activation["subject"]["runtime_git_blob_sha"] == EXPECTED_RUNTIME_BLOB
assert activation["independent_subject_verification"]["git_blob_sha"] == EXPECTED_SUBJECT_VERIFICATION_BLOB

# Activation is scheduling-only and preserves terminal truth.
assert activation["authority"] == {
    "scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
assert activation["preserved_truth"]["accepted_families"] == 5
assert activation["preserved_truth"]["open_families"] == 14
assert activation["preserved_truth"]["proved_atomic"] == 12
assert activation["preserved_truth"]["unresolved_atomic"] == 26
assert activation["preserved_truth"]["root1_positive_gaps"] == 0
assert activation["accounting"]["acceptance_credit_delta"] == 0
assert activation["accounting"]["family_credit_delta"] == 0
assert activation["accounting"]["capability_credit_delta"] == 0
assert activation["accounting"]["ownership_credit_delta"] == 0

current = root["current_acceptance"]
assert current == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
    "total_families": 19,
    "total_atomic": 38,
    "terminal": False,
}

residual = root["current_residual_root_partition"]
assert residual["unresolved_total"] == 26
assert residual["root1_positive_gap_count"] == 0
assert residual["root2_only_count"] == 16
assert residual["root3_only_count"] == 7
assert residual["root2_and_root3_count"] == 3
assert residual["root2_only_count"] + residual["root2_and_root3_count"] == 19

overlay = root["scheduler_policy"]["root2_output_only_threshold_dag"]
assert overlay["activation_git_blob_sha"] == EXPECTED_ACTIVATION_BLOB
assert overlay["subject_git_blob_sha"] == EXPECTED_MANIFEST_BLOB
assert overlay["runtime_git_blob_sha"] == EXPECTED_RUNTIME_BLOB
assert overlay["verification_git_blob_sha"] == EXPECTED_SUBJECT_VERIFICATION_BLOB
assert overlay["execution_authority"] is False
assert overlay["promotion_authority"] is False
assert overlay["fresh_reality_authority"] is False
assert overlay["acceptance_credit_delta"] == 0

# Output-only precedence must end in full benchmark as last resort and cannot
# silently erase the relative-score or fresh-reality safety constraints.
precedence = overlay["scheduler_precedence"]
assert precedence[-1] == "FULL_BENCHMARK"
rules = set(activation["hard_rules"])
assert "NO_RELATIVE_RATING_INFERENCE_FROM_ABSOLUTE_BEHAVIOR_WITHOUT_VERIFIED_RELATIVE_SCORE_BRIDGE" in rules
assert "NO_FRESH_REALITY_BEFORE_SEPARATE_EXPLICIT_AUTHORITY" in rules
assert "NO_TARGET_SCORER_OR_THRESHOLD_REBASE_AFTER_BRAIN_RESULTS" in rules

print("PASS: output-only threshold DAG activation preserves terminal truth and authority boundaries")
