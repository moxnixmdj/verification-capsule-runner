import json, pathlib, subprocess
BASE="subject/root2_external_fact_overlay_pointer_20261004_sol"
FILES={
 "root":f"{BASE}/ROOT_STATE.json",
 "act":f"{BASE}/OVERLAY_ACTIVATION.json",
 "ver":f"{BASE}/OVERLAY_VERIFICATION.json",
 "v8":f"{BASE}/V8.json",
 "v8act":f"{BASE}/V8_ACTIVATION.json",
}
EXPECTED={
 "root":"7b3d11e2a7f3e4548d647a8ee6b130372873ee75",
 "act":"4e6a60814a097ef6905f487cadfe5e8264f2494a",
 "ver":"3ef8a2cb343c2748f3da31c4aea43f6664d80d90",
 "v8":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
 "v8act":"e0c0b2a25e764c875e4af4cffb3a61f05a7a58bc",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])
o={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
root,act,ver,v8,v8act=o["root"],o["act"],o["ver"],o["v8"],o["v8act"]

# Terminal truth preserved.
assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
assert root["current_residual_root_partition"]["unresolved_total"]==26
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert root["current_residual_root_partition"]["root2_only_count"]==16
assert root["current_residual_root_partition"]["root3_only_count"]==7
assert root["current_residual_root_partition"]["root2_and_root3_count"]==3

# Active Root2 frontier remains verified V8.
ctl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctl["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert ctl["current_frontier_git_blob_sha"]==EXPECTED["v8"]
assert ctl["current_frontier_activation_git_blob_sha"]==EXPECTED["v8act"]
assert ctl["effective_scheduling_authority"] is True
assert ctl["fresh_reality_authority"] is False

# Overlay pointer exact and scheduling-only.
p=ctl["external_fact_acquisition_overlay"]
assert p["activation_git_blob_sha"]==EXPECTED["act"]
assert p["verification_git_blob_sha"]==EXPECTED["ver"]
assert p["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__SCHEDULING_ONLY__ANTI_WISHFUL_OUTREACH__ZERO_CREDIT"
assert p["self_service_fact_count"]==6
assert p["owner_exclusive_fact_count"]==6
assert p["owner_or_direct_platform_receipt_count"]==1
assert p["dormant_fact_count"]==1
assert p["low_value_support_waits"]==0
assert p["fresh_reality_authority"] is False

# Activation is backed by successful independent runner and has no execution/promotion/fresh reality authority.
assert act["verification"]["git_blob_sha"]==EXPECTED["ver"]
assert act["verification"]["conclusion"]=="success"
assert act["authority"]=={
 "scheduling":True,"effective_scheduling":True,
 "execution":False,"promotion":False,"fresh_reality":False
}
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["independent_runner"]["pull_request"]==1642
assert ver["independent_runner"]["workflow_run_id"]==37172822097
assert ver["independent_runner"]["workflow_job_id"]==111349112497

# Canonical scheduler explicitly enforces the new behavior.
sched=root["scheduler_policy"]
assert sched["root2_external_fact_acquisition_overlay"]=="canonical/governance/ROOT2_EXTERNAL_FACT_ACQUISITION_OVERLAY_ACTIVATION_V1.json"
assert sched["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True
assert sched["self_service_facts_are_owner_waits"] is False
assert sched["fresh_reality_before_zero_reality_fixed_point"] is False

# Zero-credit invariant.
assert root["accounting"]=={
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,
 "new_reality_units_consumed":0,"incremental_spend_usd":0
}
print("PASS: canonical terminal authority binds independently verified external-fact acquisition overlay")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved preserved")
print("PASS: low-value free-tier/trial/quota support outreach is forbidden in scheduler")
print("PASS: self-service facts are not owner waits; no fresh-reality authority")
