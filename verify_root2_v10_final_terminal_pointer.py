import json, pathlib, subprocess
BASE="subject/root2_v10_final_terminal_pointer_20261004_sol"
FILES={
 "root":f"{BASE}/ROOT_STATE.json",
 "v10":f"{BASE}/V10.json",
 "v10ver":f"{BASE}/V10_COMPOSITION_VERIFICATION.json",
 "finalact":f"{BASE}/V10_FINAL_ACTIVATION.json",
 "ptrver":f"{BASE}/V10_POINTER_PROJECTION_VERIFICATION.json",
 "overlayact":f"{BASE}/OVERLAY_V2_ACTIVATION.json",
 "routever":f"{BASE}/V10_ROUTING_VERIFICATION.json",
 "srcact":f"{BASE}/PRIMARY_SOURCE_ACTIVATION.json",
 "srcactver":f"{BASE}/PRIMARY_SOURCE_ACTIVATION_VERIFICATION.json",
}
EXPECTED={
 "root":"59711b491e5f4c94661f78401e66ea1f546f96c7",
 "v10":"2012926814d0d06405da56da64e589b06fef1756",
 "v10ver":"226832c5e9d5f4121f26d93bd645ed51dce474fe",
 "finalact":"f5eda02fcc104bc8a5e13a82bfc8ec3d9515dcb2",
 "ptrver":"73fce958517f0467666bc9e70f8411fa618b5210",
 "overlayact":"400cf1fa6516d384b8781201841c3359851b070b",
 "routever":"5e5bf1082a8d7ce5b1fcd2c7b16a4d9d8acdc76d",
 "srcact":"8a5eca1f9426ac015ad38c4c61bcbf8dc7eac5cb",
 "srcactver":"0105aba61eb58ea2ac069f563999031cabf469fc",
}
def blob(p):
 return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
 got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])
o={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
root,v10,v10ver,finalact,ptrver,overlayact,routever,srcact,srcactver=[o[k] for k in ("root","v10","v10ver","finalact","ptrver","overlayact","routever","srcact","srcactver")]

# Terminal truth unchanged.
assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
assert root["current_residual_root_partition"]["unresolved_total"]==26
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert root["current_residual_root_partition"]["root2_only_count"]==16
assert root["current_residual_root_partition"]["root3_only_count"]==7
assert root["current_residual_root_partition"]["root2_and_root3_count"]==3

# Active Root2 V10 exact pointers.
ctl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctl["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert ctl["current_frontier_git_blob_sha"]==EXPECTED["v10"]
assert ctl["current_frontier_verification_git_blob_sha"]==EXPECTED["v10ver"]
assert ctl["current_frontier_activation_path"]=="canonical/governance/ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1.json"
assert ctl["current_frontier_activation_git_blob_sha"]==EXPECTED["finalact"]
assert ctl["effective_scheduling_authority"] is True
assert ctl["fresh_reality_authority"] is False
assert ctl["status"]=="ACTIVE__ROOT2_FRONTIER_V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS__ZERO_CREDIT"

# Final activation itself is scheduling-only and backed by both independent verifications.
assert finalact["frontier"]["git_blob_sha"]==EXPECTED["v10"]
assert finalact["composition_verification"]["git_blob_sha"]==EXPECTED["v10ver"]
assert finalact["pointer_projection_verification"]["git_blob_sha"]==EXPECTED["ptrver"]
assert finalact["acquisition_overlay_activation"]["git_blob_sha"]==EXPECTED["overlayact"]
assert finalact["acquisition_routing_verification"]["git_blob_sha"]==EXPECTED["routever"]
assert finalact["authority"]=={
 "scheduling":True,"effective_scheduling":True,
 "execution":False,"promotion":False,"fresh_reality":False
}
assert v10ver["independent_runner"]["conclusion"]=="success"
assert ptrver["independent_runner"]["conclusion"]=="success"
assert routever["independent_runner"]["conclusion"]=="success"

# V10-safe external fact overlay exact.
ov=ctl["external_fact_acquisition_overlay"]
assert ov["activation_path"]=="canonical/governance/ROOT2_EXTERNAL_FACT_ACQUISITION_OVERLAY_V2_ACTIVATION_V1.json"
assert ov["activation_git_blob_sha"]==EXPECTED["overlayact"]
assert ov["verification_git_blob_sha"]==EXPECTED["routever"]
assert ov["self_service_fact_count"]==9
assert ov["owner_exclusive_fact_count"]==6
assert ov["owner_or_direct_platform_receipt_count"]==1
assert ov["dormant_fact_count"]==2
assert ov["low_value_support_waits"]==0
assert ov["fresh_reality_authority"] is False
assert overlayact["authority"]=={
 "scheduling":True,"effective_scheduling":True,
 "execution":False,"promotion":False,"fresh_reality":False
}

# Primary-source deletion controls preserved.
ps=ctl["primary_source_search_deletions"]
assert ps["activation_git_blob_sha"]==EXPECTED["srcact"]
assert ps["activation_verification_git_blob_sha"]==EXPECTED["srcactver"]
assert ps["scheduler_deletion_count"]==6
assert ps["fresh_reality_authority"] is False
assert srcactver["independent_runner"]["conclusion"]=="success"

# Scheduler policy exact.
sched=root["scheduler_policy"]
assert sched["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert sched["root2_effective_scheduling_authority"] is True
assert sched["root2_external_fact_acquisition_overlay"]=="canonical/governance/ROOT2_EXTERNAL_FACT_ACQUISITION_OVERLAY_V2_ACTIVATION_V1.json"
assert sched["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True
assert sched["self_service_facts_are_owner_waits"] is False
assert sched["repeat_search_for_deleted_primary_source_classes_forbidden"] is True
assert sched["fresh_reality_before_zero_reality_fixed_point"] is False
assert sched["stale_scheduler_execution_forbidden"] is True

# Zero-credit invariant.
assert root["accounting"]=={
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,
 "new_reality_units_consumed":0,"incremental_spend_usd":0
}
print("PASS: Root2 V10 is exact effective scheduling authority")
print("PASS: V10 external fact overlay routes 18 facts as 9 self-service / 6 owner / 1 owner-direct / 2 dormant")
print("PASS: anti-wishful-outreach and six primary-source deletions preserved")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved unchanged")
print("PASS: zero credit, zero spend, no execution/promotion/fresh-reality authority")
