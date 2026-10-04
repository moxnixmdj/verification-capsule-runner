#!/usr/bin/env python3
import json, pathlib, subprocess

BASE="subject/adaptive_v2_final_pointer_20261004_sol"
FILES={
  "root":f"{BASE}/ROOT_STATE.json",
  "final":f"{BASE}/FINAL_ACTIVATION.json",
  "staged":f"{BASE}/STAGED_ACTIVATION.json",
  "actver":f"{BASE}/ACTIVATION_VERIFICATION.json",
  "root2":f"{BASE}/ROOT2_V10_FINAL.json",
  "root3":f"{BASE}/ROOT3_V2.json",
  "retrieval":f"{BASE}/RETRIEVAL_AUTHORITY.json",
}
EXPECTED={
  "root":"71575e1dc3a9814e19daac25d3067890496ec9c6",
  "final":"e3d0be5e5a7296ef599c6b33a13ed599b3242471",
  "staged":"0a70eb7ff3cfbe07e4765f2e490351fbaa505030",
  "actver":"61e374593ab3ef2867021532f92be06580c348b0",
  "root2":"f5eda02fcc104bc8a5e13a82bfc8ec3d9515dcb2",
  "root3":"4d8ce78ebe312100bbfc524062199961c0c6479d",
  "retrieval":"55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

o={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
root=o["root"]; final=o["final"]; staged=o["staged"]; actver=o["actver"]
root2=o["root2"]; root3=o["root3"]; retrieval=o["retrieval"]

# Terminal truth unchanged.
assert root["current_acceptance"]=={
  "accepted_families":5,"open_families":14,"proved_atomic":12,
  "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
res=root["current_residual_root_partition"]
assert (res["unresolved_total"],res["root1_positive_gap_count"],res["root2_only_count"],
        res["root3_only_count"],res["root2_and_root3_count"])==(26,0,16,7,3)

# Root2 V10 domain authority remains exact and scheduling-only.
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert r2["current_frontier_activation_git_blob_sha"]==EXPECTED["root2"]
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False
assert root2["authority"]=={
  "scheduling":True,"effective_scheduling":True,
  "execution":False,"promotion":False,"fresh_reality":False
}

# Anti-wishful outreach remains active.
sched=root["scheduler_policy"]
assert sched["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True
assert sched["self_service_facts_are_owner_waits"] is False
assert sched["repeat_search_for_deleted_primary_source_classes_forbidden"] is True
overlay=r2["external_fact_acquisition_overlay"]
assert overlay["low_value_support_waits"]==0
assert overlay["self_service_fact_count"]==9
assert overlay["owner_exclusive_fact_count"]==6
assert overlay["owner_or_direct_platform_receipt_count"]==1
assert overlay["dormant_fact_count"]==2

# Final adaptive meta-scheduler pointer is exact.
meta=sched["adaptive_meta_scheduler"]
assert meta["final_activation_path"]=="canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2_FINAL_ACTIVATION_V1.json"
assert meta["final_activation_git_blob_sha"]==EXPECTED["final"]
assert meta["staged_activation_git_blob_sha"]==EXPECTED["staged"]
assert meta["activation_verification_git_blob_sha"]==EXPECTED["actver"]
assert meta["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__ADAPTIVE_V2_META_SCHEDULER__SCHEDULING_ONLY__ZERO_CREDIT"
assert meta["scheduling_authority"] is True
assert meta["meta_scheduling_authority"] is True
assert meta["execution_authority"] is False
assert meta["promotion_authority"] is False
assert meta["fresh_reality_authority"] is False

# Final activation chains to the independently verified staged activation and preserves domain gates.
assert final["policy"]["git_blob_sha"]=="c5b9a287b51c0594f7925770f0f22fbbbb2738dc"
assert final["runtime"]["git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert final["staged_activation"]["git_blob_sha"]==EXPECTED["staged"]
assert final["activation_verification"]["git_blob_sha"]==EXPECTED["actver"]
assert final["activation_verification"]["conclusion"]=="success"
assert final["domain_authorities"]["root2"]["git_blob_sha"]==EXPECTED["root2"]
assert final["domain_authorities"]["root3"]["git_blob_sha"]==EXPECTED["root3"]
assert final["domain_authorities"]["retrieval"]["git_blob_sha"]==EXPECTED["retrieval"]
assert final["authority"]=={
  "scheduling":True,"meta_scheduling":True,
  "execution":False,"promotion":False,"fresh_reality":False
}
assert all(v==0 for v in final["accounting"].values())

# Existing activation verification independently passed.
assert actver["independent_runner"]["conclusion"]=="success"
assert actver["verified"]["meta_scheduling_authority"] is True
assert actver["verified"]["root2_v10_domain_gate_preserved"] is True
assert actver["verified"]["root3_v2_zero_runnable_gate_preserved"] is True
assert actver["verified"]["retrieval_v19_entrypoint_v4_preserved"] is True
assert actver["verified"]["execution_authority"] is False
assert actver["verified"]["promotion_authority"] is False
assert actver["verified"]["fresh_reality_authority"] is False

# Root3 remains event-driven with zero runnable actions and no fresh reality.
assert root3["derivation"]["live_root3_predicates"]==10
assert len(root3["minimum_event_classes"])==3
assert "ZERO_CURRENT_RUNNABLE_ACTIONS" in root3["status"]
assert root3["fresh_reality_authority"] is False
assert root["root3_current_execution_state"]["currently_runnable_event_count"]==0
assert root["root3_current_execution_state"]["fresh_reality_authority"] is False

# Retrieval V19/current entrypoint remains the mandatory retrieval authority.
assert str(retrieval["status"]).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS")
v19=retrieval["v19_verified_route_portfolio"]
assert v19["entrypoint_v4_path"]=="canonical/runtime/global_retrieval_entrypoint_v4.py"
assert v19["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert retrieval["execution_authority"] is False
assert retrieval["promotion_authority"] is False
assert retrieval["policy"]["open_world_miss"]=="UNKNOWN__NEVER_NONEXISTENT"

# No credit or hidden reality leaked in via pointer repair.
assert root["accounting"]=={
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0
}
assert staged["authority"]["execution"] is False
assert staged["authority"]["promotion"] is False
assert staged["authority"]["fresh_reality"] is False

print("PASS: adaptive V2 final pointer is exact and independently chained")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved unchanged")
print("PASS: Root2 V10, Root3 V2 and Retrieval V19 domain gates preserved")
print("PASS: anti-wishful outreach remains active with zero low-value support waits")
print("PASS: zero spend, zero terminal cases, zero acceptance credit, no fresh-reality authority")
