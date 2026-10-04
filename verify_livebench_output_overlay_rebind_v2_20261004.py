from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_output_overlay_rebind_v2_20261004"

V1 = SUB / "LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V1.json"
V2 = SUB / "LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2.json"
BEFORE = SUB / "TERMINAL_ROOT_CAUSE_STATE_BEFORE.json"
AFTER = SUB / "TERMINAL_ROOT_CAUSE_STATE_AFTER.json"

EXPECTED = {
    V1: "08929577573866dc2bead65a19a856a6b4e152d2",
    V2: "39da9be4a63c4688a4ecc8a876b094b6e211ce97",
    BEFORE: "e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
    AFTER: "601e82d00104b4ed36ee5968ad966a0c02e627c1",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for path, expected in EXPECTED.items():
    assert git_blob_sha(path) == expected, (path, git_blob_sha(path), expected)

v1 = json.loads(V1.read_text())
v2 = json.loads(V2.read_text())
before = json.loads(BEFORE.read_text())
after = json.loads(AFTER.read_text())

# Prove the root delta is literally one new scheduling overlay.
before_normalized = copy.deepcopy(before)
after_normalized = copy.deepcopy(after)
overlay = after_normalized["scheduler_policy"].pop("root2_output_only_threshold_dag")
assert "root2_output_only_threshold_dag" not in before_normalized["scheduler_policy"]
assert before_normalized == after_normalized

assert overlay["execution_authority"] is False
assert overlay["promotion_authority"] is False
assert overlay["fresh_reality_authority"] is False
assert overlay["acceptance_credit_delta"] == 0
assert overlay["status"].startswith("ACTIVE_IFF_EXACT_ROOT_PROJECTION_RECEIPT_EXISTS_AND_PASSES")

# Terminal truth is byte-delta-invariant.
for doc in (before, after):
    assert doc["current_acceptance"] == {
        "accepted_families": 5,
        "open_families": 14,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "total_families": 19,
        "total_atomic": 38,
        "terminal": False,
    }
    residual = doc["current_residual_root_partition"]
    assert residual["unresolved_total"] == 26
    assert residual["root1_positive_gap_count"] == 0
    assert residual["root2_only_count"] == 16
    assert residual["root3_only_count"] == 7
    assert residual["root2_and_root3_count"] == 3
    assert "LIVEBENCH_IF_GE_65_7" in residual["root2_only"]
    assert "LIVEBENCH_IF_GE_65_7" not in residual["root3_only"]
    assert "LIVEBENCH_IF_GE_65_7" not in residual["root2_and_root3"]

# V2 is an exact authority rebind, not a widened authority grant.
assert v2["schema"] == "PROJECT_BRAIN_LIVEBENCH_CURRENT_PREDICATE_LOCAL_DIRECT_AUTHORITY_ACTIVATION_V2"
assert v2["target_predicate"] == "LIVEBENCH_IF_GE_65_7"
assert v2["authorized_predicates"] == ["LIVEBENCH_IF_GE_65_7"]
assert v2["authority_basis"]["previous_activation"]["git_blob_sha"] == EXPECTED[V1]
assert v2["authority_basis"]["root_state"]["git_blob_sha"] == EXPECTED[AFTER]
delta = v2["authority_basis"]["root_state_delta"]
assert delta["prior_git_blob_sha"] == EXPECTED[BEFORE]
assert delta["current_git_blob_sha"] == EXPECTED[AFTER]
assert delta["permitted_delta"] == "ADD_SCHEDULER_POLICY_ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ONLY"

# All execution identity and firewall semantics remain exactly equal to V1.
assert v2["exact_execution_binding"] == v1["exact_execution_binding"]
assert v2["point_of_use_gates_before_any_terminal_case_read"] == v1["point_of_use_gates_before_any_terminal_case_read"]
assert v2["result_handling"] == v1["result_handling"]
assert v2["scope_firewall"] == v1["scope_firewall"]
assert v2["authority"] == v1["authority"]
assert v2["authority"] == {
    "execution": True,
    "predicate_local_fresh_reality": True,
    "global_fresh_reality": False,
    "promotion": False,
    "acceptance_credit": False,
}
assert v2["accounting"] == v1["accounting"]
assert v2["accounting"]["new_reality_units_consumed"] == 0
assert v2["accounting"]["terminal_cases_consumed"] == 0
assert v2["accounting"]["acceptance_credit_delta"] == 0

# Threshold overlay itself preserves the LiveBench frozen target rather than
# silently changing it.
assert v2["exact_execution_binding"]["threshold_percent"] == 65.7
assert v2["exact_execution_binding"]["population_count"] == 200
assert v2["exact_execution_binding"]["candidate_commit"] == "d5de4f5808dced840da34d051e3f9a5ff06e2e54"
assert v2["exact_execution_binding"]["candidate_tree"] == "fd39e966d4686c7317b9a1558b360eb0c58ad76f"

print("PASS: LiveBench scoped authority may be rebound across the verified output-only scheduling-only root delta")
