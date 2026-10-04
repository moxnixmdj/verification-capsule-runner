from __future__ import annotations
import hashlib
import json
from pathlib import Path

EXPECTED={
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "aff9dd642ce05f174374b2c9e2c7d0b282f257a2",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "2ac73aee0efd81fca9a66413ecf1097b7b049d97",
    "canonical/runtime/root2_v13_decision_only_control_plane_guard_v1.py": "12abb038ed3352f891521919dbc28742b4b2461a",
    "canonical/tests/test_root2_v13_decision_only_control_plane_guard_v1.py": "f05b1089f0266aa25aac76d829e8af7ef2a88539",
    "canonical/governance/ROOT2_V13_DECISION_ONLY_CONTROL_PLANE_RECONCILIATION_CANDIDATE_V1.json": "9e7db3f46000489e81ddcc6ffc00f99ea224b8b1",
    "canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V13.json": "bb631b80eea5a183728fb27e2aff99bbe63f1757",
    "canonical/verification/ROOT2_FRONTIER_V13_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "dd810106cf30f101453da07e2ef37cb81d7faddd",
    "canonical/governance/ROOT2_FRONTIER_V13_FINAL_ACTIVATION_V1.json": "08c84d8f0a46ff0f13943388306195fea79ca6d7",
    "canonical/governance/ROOT2_DECISION_ONLY_EVALUATION_FINAL_ACTIVATION_V1.json": "2f8690507a16840f085bcf34da90df1593dd0226",
    "canonical/verification/ROOT2_DECISION_ONLY_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "432d15b62b70dd6f7e030aafd7239bd1a381b5ee",
    "canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json": "a76391c98767a0fa688adc32f5ac23f9caaea624"
}

def git_blob_sha(path:str)->str:
    data=Path(path).read_bytes()
    header=f"blob {len(data)}".encode()+bytes([0])
    return hashlib.sha1(header+data).hexdigest()

for path,want in EXPECTED.items():
    got=git_blob_sha(path)
    assert got==want,(path,want,got)

from canonical.runtime.root2_v13_decision_only_control_plane_guard_v1 import verify
out=verify()
assert out["status"]=="PASS"
assert out["counts_preserved_5_12_26"] is True
assert out["root2_v13_projection_exact"] is True
assert out["decision_only_projection_exact"] is True
assert out["stale_v10_instruction_deleted"] is True
assert out["v14_through_v18_not_promoted"] is True
assert out["arena_truth_repair_preserved"] is True
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_delta"]==0

from canonical.tests.test_root2_v13_decision_only_control_plane_guard_v1 import test_control_plane
test_control_plane()

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_V13_DECISION_ONLY_CONTROL_PLANE_INDEPENDENT_RESULT_V1",
 "status":"PASS",
 "exact_subject_blobs":True,
 "counts_preserved_5_12_26":True,
 "root2_v13_projection_exact":True,
 "decision_only_projection_exact":True,
 "stale_v10_instruction_deleted":True,
 "v14_through_v18_not_promoted":True,
 "arena_truth_repair_preserved":True,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
