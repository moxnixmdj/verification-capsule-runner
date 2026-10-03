#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

auth=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
act=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json").read_text())
core=json.loads((ROOT/"canonical/verification/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
avr=json.loads((ROOT/"canonical/verification/ROOT1_ACQUISITION_CLOSURE_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
final=json.loads((ROOT/"canonical/verification/ROOT1_V2_FINAL_RECONCILIATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())

src=auth["sources"]["terminal_root_cause_state"]
assert src["path"]=="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
assert src["git_blob_sha"]=="2e747250c0fb243f7cc9ae9fcd0fd71732761b8f"
assert "ROOT1_INACTIVE" in src["status"]
assert "V2_ACTIVE" in src["status"]

r1src=auth["sources"]["root1_acquisition_closure_v2"]
expected={
 "governance_git_blob_sha":"2ffec0cba9fc634d9b5a0bf896cfcba839aebfc3",
 "activation_git_blob_sha":"be600d377860ca83766bf9477bbba3ced75839a9",
 "core_verification_git_blob_sha":"65493307bab65a175c7e3885cc9e6c4da24523b5",
 "activation_verification_git_blob_sha":"234c23e55e20d6a6ee07331d924882c3a68c5b24",
 "final_reconciliation_git_blob_sha":"5f3d17fed096d753d51cee95d056bed9046b23db",
}
for k,v in expected.items():
    assert r1src[k]==v,(k,r1src.get(k),v)

r1=root["roots"]["root_1_capability_missing"]
assert r1["current_positive_root1_blockers"]==[]
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert r1["active_acquisition_control"]["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT"
assert r1["active_acquisition_control"]["current_envelope_sealed"] is False

assert core["independent_runner"]["conclusion"]=="success"
assert avr["independent_runner"]["conclusion"]=="success"
assert final["independent_runner"]["conclusion"]=="success"
assert final["verified"]["root1_positive_gap_count_zero"] is True
assert final["verified"]["root1_currently_active"] is False
assert final["verified"]["frozen_envelope_unsealed"] is True
assert act["current_root1_truth"]["frozen_opus55_envelope_sealed"] is False

for obj in (core,avr,final):
    assert obj["incremental_spend_usd"]==0
    assert obj["acceptance_credit_delta"]==0
    assert obj["family_credit_delta"]==0
    assert obj["capability_credit_delta"]==0
    assert obj["ownership_credit_delta"]==0

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT1_V2_TERMINAL_AUTHORITY_RECONCILIATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__TOP_LEVEL_POINTER_CURRENT__ROOT1_V2_RECEIPTS_BOUND__ZERO_GAPS__INACTIVE__ENVELOPE_UNSEALED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
