import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())

v4=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V4.json")
vr=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V4_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
act=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V4_ACTIVATION_V1.json")
auth=load("CURRENT_TERMINAL_AUTHORITY_V1.json")
front=load("ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")

assert v4["current_inputs"]["route_inventory_git_blob_sha"]=="9f93503d6ee0ac95c63fc7a4dafc1f75f2e48294"
assert v4["current_inputs"]["comparator_vector_git_blob_sha"]=="b28af5176550aba9e44ffd8ac9fde4fa7ba388bf"
assert vr["independent_runner"]["workflow_run_id"]==37163976469
assert vr["independent_runner"]["workflow_job_id"]==111323011656
assert vr["independent_runner"]["conclusion"]=="success"
assert vr["verified"]["fixed_bar_predicates"]==15
assert vr["verified"]["unique_fixed_bar_surfaces"]==14
assert vr["verified"]["total_root2_involved_predicates"]==19
assert vr["verified"]["strict_acceptance"]=="5/19"
assert vr["verified"]["proved_atomic"]==12
assert vr["verified"]["unresolved_atomic"]==26

assert act["current_inputs"]["rebind_git_blob_sha"]=="8d3f20c8b8379b282f9b03fc73ba82f6f8946fa5"
assert act["current_inputs"]["verification_git_blob_sha"]=="b0449e7ba797a0084f6a3c74aa12a29c42f32c2d"
assert act["optimizer"]["optimizer_logic_changed"] is False
assert act["fresh_reality_authority"] is False

a=auth["sources"]["root2_hypergraph_rebind_v4"]
assert a["rebind_git_blob_sha"]=="8d3f20c8b8379b282f9b03fc73ba82f6f8946fa5"
assert a["verification_git_blob_sha"]=="b0449e7ba797a0084f6a3c74aa12a29c42f32c2d"
assert a["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert "HYPERGRAPH_V4_ACTIVE_INDEPENDENT_PASS" in auth["next_terminal_action"]

f=front["root2_fixed_bar_hypergraph_rebind"]
assert f["git_blob_sha"]=="8d3f20c8b8379b282f9b03fc73ba82f6f8946fa5"
assert f["verification_git_blob_sha"]=="b0449e7ba797a0084f6a3c74aa12a29c42f32c2d"
assert f["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert front["fresh_reality_authority"] is False

for obj in (vr,act,front):
    assert obj["incremental_spend_usd"]==0
    assert obj["acceptance_credit_delta"]==0
    assert obj["family_credit_delta"]==0
    assert obj["capability_credit_delta"]==0
    assert obj["ownership_credit_delta"]==0

print(json.dumps({
 "status":"PASS__ROOT2_HYPERGRAPH_V4_ACTIVATION_PROJECTION__CURRENT_ROUTE_STATE_BOUND__OPTIMIZER_LOGIC_UNCHANGED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
