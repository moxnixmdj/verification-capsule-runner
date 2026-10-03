#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
act=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json").read_text())
vr=json.loads((ROOT/"canonical/verification/ROOT1_ACQUISITION_CLOSURE_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
r1=root["roots"]["root_1_capability_missing"]
ctrl=r1["active_acquisition_control"]
assert r1["current_positive_root1_blockers"]==[]
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert root["scheduler_policy"]["root1_currently_active"] is False
assert ctrl["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT"
assert ctrl["git_blob_sha"]=="be600d377860ca83766bf9477bbba3ced75839a9"
assert ctrl["current_envelope_sealed"] is False
assert ctrl["activation_verification"]["git_blob_sha"]=="234c23e55e20d6a6ee07331d924882c3a68c5b24"
assert ctrl["activation_verification"]["conclusion"]=="success"
assert ctrl["activation_verification"]["workflow_run_id"]==37160315593
assert ctrl["activation_verification"]["workflow_job_id"]==111312237250
assert vr["independent_runner"]["conclusion"]=="success"
assert vr["verified"]["root1_positive_gap_count_zero"] is True
assert vr["verified"]["root1_inactive"] is True
assert vr["verified"]["frozen_envelope_unsealed"] is True
assert act["current_root1_truth"]["frozen_opus55_envelope_sealed"] is False
assert act["acceptance_credit_delta"]==0
assert vr["acceptance_credit_delta"]==0
print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT1_V2_FINAL_RECONCILIATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__FINAL_ROOT1_AUTHORITY_ACTIVE_VERIFIED_ZERO_GAPS__ENVELOPE_UNSEALED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
