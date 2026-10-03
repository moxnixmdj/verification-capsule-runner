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

act=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json").read_text())
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
gov=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2.json").read_text())
receipt=json.loads((ROOT/"canonical/verification/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())

assert act["operative_control"]["governance_git_blob_sha"]=="2ffec0cba9fc634d9b5a0bf896cfcba839aebfc3"
assert act["operative_control"]["runtime_git_blob_sha"]=="9683d993a99da27dffbb45a30e941e04094e1046"
assert act["operative_control"]["tests_git_blob_sha"]=="e8eb7585b33717deb56d8e5368f749f6d7d7aad4"
assert act["operative_control"]["verification_git_blob_sha"]=="65493307bab65a175c7e3885cc9e6c4da24523b5"
assert act["operative_control"]["independent_runner_workflow_run_id"]==37159994052
assert act["operative_control"]["independent_runner_job_id"]==111311273150
assert receipt["independent_runner"]["conclusion"]=="success"
assert receipt["verified"]["exact_brain_blob_identities"] is True
assert receipt["verified"]["zero_terminal_credit_preserved"] is True

r1=root["roots"]["root_1_capability_missing"]
assert r1["current_positive_root1_blockers"]==[]
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert root["scheduler_policy"]["root1_currently_active"] is False
assert r1["active_acquisition_control"]["git_blob_sha"]==manifest["exact_brain_blobs"]["canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json"]
assert r1["active_acquisition_control"]["current_envelope_sealed"] is False
assert act["current_root1_truth"]["root1_positive_gap_count"]==0
assert act["current_root1_truth"]["root1_currently_active"] is False
assert act["current_root1_truth"]["frozen_opus55_envelope_sealed"] is False
assert gov["current_envelope_claim"]["frozen_envelope_sealed"] is False

for obj in (act,receipt):
    assert obj["incremental_spend_usd"]==0
    assert obj["acceptance_credit_delta"]==0
    assert obj["family_credit_delta"]==0
    assert obj["capability_credit_delta"]==0
    assert obj["ownership_credit_delta"]==0
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT1_ACQUISITION_CLOSURE_V2_ACTIVATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_ACTIVATION_PROJECTION__ROOT1_INACTIVE_ZERO_GAPS__V2_POINTER_BOUND__ENVELOPE_UNSEALED__ZERO_CREDIT",
 "pass":True,
 "verified":{
   "exact_activation_blobs":True,
   "verified_core_pointer_bound":True,
   "independent_core_receipt_bound":True,
   "root1_positive_gap_count_zero":True,
   "root1_inactive":True,
   "frozen_envelope_unsealed":True,
   "zero_credit_preserved":True
 }
},indent=2,sort_keys=True))
