#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(rel): return json.loads((ROOT/rel).read_text())
def blob_sha(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
m=load("EXPECTED_BRAIN_BLOBS.json")
for rel,expected in m["exact_brain_blobs"].items():
    p=ROOT/rel
    got=blob_sha(p)
    assert got==expected,(rel,got,expected)

bridge=load("canonical/governance/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
receipt=load("canonical/verification/ROOT2_V5_PROJECTION_VERIFICATION_20261004_V1.json")
V5="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
V5SHA="e948022f0a4e8d91b949a5155d850d56aa137c87"
VP="canonical/verification/ROOT2_V5_PROJECTION_VERIFICATION_20261004_V1.json"
VSHA="2475a8583e2ed2889c3e9e0613ae3bcf269ffc82"

assert receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert receipt["subject_git_blob_sha"]==V5SHA
assert receipt["verifier"]["pull_request"]==1568
assert receipt["verifier"]["workflow_run_id"]==37168462917
assert receipt["verifier"]["workflow_job_id"]==111336298139
assert receipt["verifier"]["conclusion"]=="success"
assert receipt["fresh_reality_authority"] is False
assert receipt["execution_authority"] is False
assert receipt["promotion_authority"] is False

bc=bridge["root2_closure_controller_v2"]
assert bc["frontier_path"]==V5 and bc["frontier_git_blob_sha"]==V5SHA
assert bc["frontier_verification_path"]==VP and bc["frontier_verification_git_blob_sha"]==VSHA
assert bc["effective_scheduling_authority"] is False
assert "POINTER_PROJECTION_REVERIFY_PENDING" in bc["status"]
for k in ("frontier_activation_path","frontier_activation_git_blob_sha","pointer_projection_verification_path","pointer_projection_verification_git_blob_sha"):
    assert k not in bc,k
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False
assert bridge["incremental_spend_usd"]==0
assert bridge["terminal_cases_consumed"]==0
assert bridge["acceptance_credit_delta"]==0
assert "ROOT2_V5_POINTER_PROJECTION" in bridge["next"]
assert "NO_FRESH_SCORE" in bridge["next"]

rc=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert rc["current_frontier_path"]==V5 and rc["current_frontier_git_blob_sha"]==V5SHA
assert rc["current_frontier_verification_path"]==VP and rc["current_frontier_verification_git_blob_sha"]==VSHA
assert rc["effective_scheduling_authority"] is False
assert rc["fresh_reality_authority"] is False
assert "POINTER_PROJECTION_REVERIFY_PENDING" in rc["status"]
for k in ("current_frontier_activation_path","current_frontier_activation_git_blob_sha","pointer_projection_verification_path","pointer_projection_verification_git_blob_sha"):
    assert k not in rc,k
sp=root["scheduler_policy"]
assert sp["root2_current_frontier"]==V5
assert sp["root2_effective_scheduling_authority"] is False
acc=root["current_acceptance"]
assert (acc["accepted_families"],acc["open_families"],acc["proved_atomic"],acc["unresolved_atomic"],acc["terminal"])==(5,14,12,26,False)
part=root["current_residual_root_partition"]
assert (part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(16,7,3)
r3=root["root3_current_execution_state"]
assert r3["path"]=="canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json"
assert r3["live_root3_predicates"]==10
assert r3["matched_scope_targets"]==7
assert r3["event_class_count"]==3
assert r3["currently_runnable_event_count"]==0
assert r3["fresh_reality_authority"] is False

s=auth["sources"]["root2_closure_v2_current_frontier"]
assert s["path"]==V5 and s["git_blob_sha"]==V5SHA
assert s["verification"]==VP and s["verification_git_blob_sha"]==VSHA
assert s["effective_scheduling_authority"] is False
assert "POINTER_PROJECTION_REVERIFY_PENDING" in s["status"]
for k in ("activation","activation_git_blob_sha","pointer_projection_verification","pointer_projection_verification_git_blob_sha"):
    assert k not in s,k
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["achieved"] is False
assert "NO_FRESH_REALITY" in auth["next_terminal_action"]
assert "NO_TERMINAL_CASES" in auth["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_V5_POINTER_COHERENCE_PUBLIC_RUNNER_RESULT_V1",
 "status":"PASS__ALL_THREE_POINTER_SURFACES_COHERENT_ON_VERIFIED_V5__SCHEDULING_INEFFECTIVE__NO_DANGLING_ACTIVATION__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
