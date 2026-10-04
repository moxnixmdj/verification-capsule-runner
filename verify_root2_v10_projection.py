import json, pathlib, subprocess

P={
 "frontier":"verification_inputs/root2_v10_projection_frontier.json",
 "activation":"verification_inputs/root2_v10_projection_activation.json",
 "terminal":"verification_inputs/root2_v10_projection_terminal.json",
 "root":"verification_inputs/root2_v10_projection_root.json",
 "bridge":"verification_inputs/root2_v10_projection_bridge.json",
}
H={
 "frontier":"2012926814d0d06405da56da64e589b06fef1756",
 "activation":"dc2605176a10982d4d700faea951f8e11d043a1f",
 "terminal":"163e3f0f932ff69b111f90648e5865cc460797e8",
 "root":"680725c06555fb394d0539bf1bbecc390fd15453",
 "bridge":"212cd88d752b13deef5eb04c32c4170b000bf7fa",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in P.items():
    got=blob(p); assert got==H[k],(k,got,H[k])
load=lambda p: json.loads(pathlib.Path(p).read_text())
f,a,t,r,b=[load(P[k]) for k in ("frontier","activation","terminal","root","bridge")]

assert f["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10"
assert f["exact_state"]["accepted_families"]==5
assert f["exact_state"]["open_families"]==14
assert f["exact_state"]["proved_atomic"]==12
assert f["exact_state"]["unresolved_atomic"]==26
assert f["accounting"]["incremental_spend_usd"]==0
assert f["accounting"]["terminal_cases_consumed"]==0
assert f["fresh_reality_authority"] is False

assert a["frontier_git_blob_sha"]==H["frontier"]
assert a["verification_git_blob_sha"]=="226832c5e9d5f4121f26d93bd645ed51dce474fe"
assert a["authority"]["effective_scheduling"] is False
assert a["authority"]["execution"] is False
assert a["authority"]["promotion"] is False
assert a["authority"]["fresh_reality"] is False

tp=t["sources"]["root2_closure_v2_current_frontier"]
assert tp["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert tp["git_blob_sha"]==H["frontier"]
assert tp["verification_git_blob_sha"]=="226832c5e9d5f4121f26d93bd645ed51dce474fe"
assert tp["activation_git_blob_sha"]==H["activation"]
assert tp["effective_scheduling_authority"] is False

rp=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert rp["current_frontier_git_blob_sha"]==H["frontier"]
assert rp["current_frontier_verification_git_blob_sha"]=="226832c5e9d5f4121f26d93bd645ed51dce474fe"
assert rp["current_frontier_activation_git_blob_sha"]==H["activation"]
assert rp["effective_scheduling_authority"] is False
assert rp["fresh_reality_authority"] is False

# The independently verified anti-wishful-outreach overlay must survive the frontier swap.
ov=rp["external_fact_acquisition_overlay"]
assert ov["activation_git_blob_sha"]=="4e6a60814a097ef6905f487cadfe5e8264f2494a"
assert ov["verification_git_blob_sha"]=="3ef8a2cb343c2748f3da31c4aea43f6664d80d90"
assert ov["low_value_support_waits"]==0
assert ov["self_service_fact_count"]==6
assert ov["owner_exclusive_fact_count"]==6
assert ov["owner_or_direct_platform_receipt_count"]==1
assert ov["dormant_fact_count"]==1
assert ov["fresh_reality_authority"] is False

sp=r["scheduler_policy"]
assert sp["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert sp["root2_effective_scheduling_authority"] is False
assert sp["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True
assert sp["self_service_facts_are_owner_waits"] is False
assert sp["root2_external_fact_acquisition_overlay"]=="canonical/governance/ROOT2_EXTERNAL_FACT_ACQUISITION_OVERLAY_ACTIVATION_V1.json"

bp=b["root2_closure_controller_v2"]
assert bp["frontier_git_blob_sha"]==H["frontier"]
assert bp["frontier_verification_git_blob_sha"]=="226832c5e9d5f4121f26d93bd645ed51dce474fe"
assert bp["frontier_activation_git_blob_sha"]==H["activation"]
assert bp["effective_scheduling_authority"] is False
assert b["execution_authority"] is False
assert b["promotion_authority"] is False
assert b["fresh_reality_authority"] is False

print("ROOT2_V10_PROJECTION_PASS__POINTER_COHERENT__OUTREACH_AND_SOURCE_DELETIONS_PRESERVED__EFFECTIVE_SCHEDULING_FALSE__ZERO_CREDIT")
