#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()
def load(rel):
    return json.loads((ROOT/rel).read_text())

m=load("EXPECTED_BRAIN_BLOBS.json")
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

front=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json")
prior=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_ACTIVATION_V1.json")
front_verify=load("canonical/verification/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
controller=load("canonical/governance/ROOT2_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json")
final=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_EFFECTIVE_SCHEDULING_ACTIVATION_V1.json")
bridge=load("canonical/governance/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

assert front["root2_touching_predicates"]==19
assert front["execution_authority"] is False
assert front["promotion_authority"] is False
assert front["fresh_reality_authority"] is False
assert front["accounting"]["incremental_spend_usd"]==0
assert front["accounting"]["terminal_cases_consumed"]==0
assert front["accounting"]["acceptance_credit_delta"]==0

assert prior["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert prior["authority"]["effective_scheduling_authority"] is False
assert prior["authority"]["execution_authority"] is False
assert prior["authority"]["fresh_reality_authority"] is False
assert front_verify["independent_runner"]["conclusion"]=="success"
assert controller["authority"]["execution_authority"] is False
assert controller["authority"]["fresh_reality_authority"] is False

assert final["activation_condition_evaluation"]=={
    "frontier_subject_independent_pass": True,
    "pointer_projection_independent_pass": True,
    "current_authority_binds_exact_frontier_and_activation": True,
    "condition_satisfied": True,
}
pp=final["pointer_projection"]
assert pp["brain_pull_request"]==1522
assert pp["brain_merge_commit"]=="cad4d71ddcc66b3ea0a0cc636687d71dfc94cac2"
assert pp["verifier_pull_request"]==1561
assert pp["verifier_merge_commit"]=="aca3d2166876c401711bc083dc9eb4ea83ffee65"
assert pp["workflow_run_id"]==37167775499
assert pp["workflow_job_id"]==111334245344
assert pp["conclusion"]=="success"
fa=final["authority"]
assert fa["scheduling_authority"] is True
assert fa["effective_scheduling_authority"] is True
assert fa["execution_authority"] is False
assert fa["promotion_authority"] is False
assert fa["fresh_reality_authority"] is False
assert fa["comparator_rebase_authority"] is False
assert final["accounting"]=={
    "incremental_spend_usd":0,
    "new_reality_units_consumed":0,
    "terminal_cases_consumed":0,
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0
}

b=bridge["root2_closure_controller_v2"]
assert b["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert b["effective_scheduling_authority"] is True
assert b["effective_scheduling_activation_git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_EFFECTIVE_SCHEDULING_ACTIVATION_V1.json"]
assert "INDEPENDENT_REVERIFY_PENDING" in b["status"]
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False
assert bridge["incremental_spend_usd"]==0
assert bridge["terminal_cases_consumed"]==0

acc=root["current_acceptance"]
assert (acc["accepted_families"],acc["open_families"])==(5,14)
assert (acc["proved_atomic"],acc["unresolved_atomic"])==(12,26)
assert acc["terminal"] is False
part=root["current_residual_root_partition"]
assert (part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(16,7,3)
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False
assert r2["effective_scheduling_activation_git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_EFFECTIVE_SCHEDULING_ACTIVATION_V1.json"]
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True

src=auth["sources"]["root2_closure_v2_current_frontier"]
assert src["git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert src["effective_scheduling_authority"] is True
assert src["effective_scheduling_activation_git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_EFFECTIVE_SCHEDULING_ACTIVATION_V1.json"]
assert "INDEPENDENT_REVERIFY_PENDING" in src["status"]
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["achieved"] is False
assert "NO_FRESH_REALITY" in auth["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_V3_EFFECTIVE_SCHEDULING_ACTIVATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EFFECTIVE_SCHEDULING_ONLY__COUNTS_PRESERVED__EXECUTION_PROMOTION_FRESH_REALITY_FALSE__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
