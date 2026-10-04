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
circle=load("canonical/governance/TB4_CIRCLECI_GEN2_FREE_PLAN_CARRIER_CANDIDATE_20261004_V1.json")
verify=load("canonical/verification/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
act=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_ACTIVATION_V1.json")
bridge=load("canonical/governance/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
controller=load("canonical/governance/ROOT2_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json")

assert verify["independent_runner"]["conclusion"]=="success"
assert verify["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert verify["subject"]["circleci_candidate_git_blob_sha"]=="b855ce5c4d8f192cb806be468a8d5c1e7c2f2a93"
assert verify["subject"]["buildkite_candidate_git_blob_sha"]=="2725cf6820fb7ce6025213d474b9acf2937282ee"
assert verify["verified"]["synthesis_remaining"]==["metric:matched_quality","matched_quality_noninferiority"]
assert verify["verified"]["circleci_disk_runtime_allowance_admissibility_unproved"] is True

assert act["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert act["verification"]["git_blob_sha"]=="a7495e97c008fb74355af04e56bf75ca5c8ec8e8"
assert act["authority"]["scheduling_authority"] is True
assert act["authority"]["effective_scheduling_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False
assert "POINTER_PROJECTION_REVERIFY_REQUIRED" in act["status"]

for obj in (bridge,root,auth,front,circle,verify,act,controller):
    if "fresh_reality_authority" in obj:
        assert obj["fresh_reality_authority"] is False

b=bridge["root2_closure_controller_v2"]
assert b["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert b["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert b["frontier_activation_git_blob_sha"]=="6b38665671f36096d54fd68eff95b41fea6e7bc7"
assert b["frontier_verification_git_blob_sha"]=="a7495e97c008fb74355af04e56bf75ca5c8ec8e8"
assert "PENDING" in b["status"]

r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert r2["current_frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert r2["current_frontier_activation_git_blob_sha"]=="6b38665671f36096d54fd68eff95b41fea6e7bc7"
assert r2["current_frontier_verification_git_blob_sha"]=="a7495e97c008fb74355af04e56bf75ca5c8ec8e8"
assert "PENDING" in r2["status"]
assert root["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"

part=root["current_residual_root_partition"]
assert part["unresolved_total"]==26
assert part["root1_positive_gap_count"]==0
assert part["root2_only_count"]==16
assert part["root3_only_count"]==7
assert part["root2_and_root3_count"]==3
acc=root["current_acceptance"]
assert acc["accepted_families"]==5
assert acc["open_families"]==14
assert acc["proved_atomic"]==12
assert acc["unresolved_atomic"]==26
assert acc["terminal"] is False

src=auth["sources"]["root2_closure_v2_current_frontier"]
assert src["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert src["git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert src["activation_git_blob_sha"]=="6b38665671f36096d54fd68eff95b41fea6e7bc7"
assert src["verification_git_blob_sha"]=="a7495e97c008fb74355af04e56bf75ca5c8ec8e8"
assert "PENDING" in src["status"]
assert "V3_POINTER_PROJECTION_PENDING" in auth["next_terminal_action"]

providers={x["provider"] for x in front["tb4_carrier_portfolio"]["candidates"]}
assert providers=={"Buildkite","CircleCI"}
assert circle["narrow_conclusion"]["tb4_carrier_admissibility_proved"] is False
assert front["execution_authority"] is False
assert front["promotion_authority"] is False
assert front["fresh_reality_authority"] is False
assert front["accounting"]["terminal_cases_consumed"]==0
assert front["accounting"]["incremental_spend_usd"]==0
assert front["accounting"]["acceptance_credit_delta"]==0

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_FRONTIER_V3_POINTER_PROJECTION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_V3_POINTER_PROJECTION__COUNTS_PRESERVED__EFFECTIVE_SCHEDULING_STILL_FALSE__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
