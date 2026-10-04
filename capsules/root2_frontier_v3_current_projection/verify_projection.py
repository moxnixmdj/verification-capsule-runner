#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

def load(rel):
    return json.loads((ROOT/rel).read_text())

front=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json")
act=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_ACTIVATION_V1.json")
vr=load("canonical/verification/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
bridge=load("canonical/governance/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
controller=load("canonical/governance/ROOT2_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json")

assert front["root2_touching_predicates"]==19
assert front["accounting"]["incremental_spend_usd"]==0
assert front["accounting"]["terminal_cases_consumed"]==0
assert front["accounting"]["acceptance_credit_delta"]==0
assert front["execution_authority"] is False
assert front["promotion_authority"] is False
assert front["fresh_reality_authority"] is False
assert {x["provider"] for x in front["tb4_carrier_portfolio"]["candidates"]}=={"Buildkite","CircleCI"}

assert vr["independent_runner"]["conclusion"]=="success"
assert vr["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert vr["verified"]["tb4_carrier_admissibility_proved"] is False
assert vr["verified"]["fresh_reality_authority"] is False
assert vr["verified"]["terminal_cases_consumed"]==0

assert act["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert act["verification"]["git_blob_sha"]=="8436a9eb30312b959ba094394e60f26b4833a3a2"
assert act["authority"]["scheduling_authority"] is True
assert act["authority"]["effective_scheduling_authority"] is False
assert act["authority"]["execution_authority"] is False
assert act["authority"]["promotion_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False
assert "POINTER_PROJECTION_REVERIFY_REQUIRED" in act["status"]

b=bridge["root2_closure_controller_v2"]
assert b["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert b["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert b["frontier_activation_git_blob_sha"]=="76d36bc34947e726502d0c8fc1dbb961d6442c88"
assert b["frontier_verification_git_blob_sha"]=="8436a9eb30312b959ba094394e60f26b4833a3a2"
assert "PENDING" in b["status"]
assert bridge["fresh_reality_authority"] is False
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False

r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert r2["current_frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert r2["current_frontier_activation_git_blob_sha"]=="76d36bc34947e726502d0c8fc1dbb961d6442c88"
assert r2["current_frontier_verification_git_blob_sha"]=="8436a9eb30312b959ba094394e60f26b4833a3a2"
assert "PENDING" in r2["status"]
assert r2["fresh_reality_authority"] is False
assert root["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"

acc=root["current_acceptance"]
assert (acc["accepted_families"],acc["open_families"])==(5,14)
assert (acc["proved_atomic"],acc["unresolved_atomic"])==(12,26)
assert acc["terminal"] is False
part=root["current_residual_root_partition"]
assert part["unresolved_total"]==26
assert part["root1_positive_gap_count"]==0
assert part["root2_only_count"]==16
assert part["root3_only_count"]==7
assert part["root2_and_root3_count"]==3

src=auth["sources"]["root2_closure_v2_current_frontier"]
assert src["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert src["git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert src["activation_git_blob_sha"]=="76d36bc34947e726502d0c8fc1dbb961d6442c88"
assert src["verification_git_blob_sha"]=="8436a9eb30312b959ba094394e60f26b4833a3a2"
assert "PENDING" in src["status"]
assert "V3_POINTER_PROJECTION_PENDING" in auth["next_terminal_action"]

assert controller["authority"]["fresh_reality_authority"] is False
assert controller["authority"]["execution_authority"] is False
assert controller["current_root2_state"]["root2_touching"]==19
assert controller["current_root2_state"]["total_unresolved"]==26
assert controller["current_root2_state"]["accepted_families"]==5
assert controller["current_root2_state"]["proved_atomic"]==12

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_FRONTIER_V3_CURRENT_PROJECTION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_CURRENT_MAIN_V3_POINTER_PROJECTION__COUNTS_PRESERVED__FAIL_CLOSED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
