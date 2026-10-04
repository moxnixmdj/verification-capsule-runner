import json, pathlib, subprocess
BASE="subject/root2_primary_source_deletions_pointer_20261004_sol"
FILES={
 "root":f"{BASE}/ROOT_STATE.json",
 "act":f"{BASE}/SOURCE_ACTIVATION.json",
 "actver":f"{BASE}/SOURCE_ACTIVATION_VERIFICATION.json",
 "src":f"{BASE}/SOURCE_REFRESH.json",
 "srcver":f"{BASE}/SOURCE_VERIFICATION.json",
 "overlay":f"{BASE}/EXTERNAL_FACT_OVERLAY_ACTIVATION.json",
}
EXPECTED={
 "root":"e163d8b6fdd86afe9759defb24d920172de12afb",
 "act":"8a5eca1f9426ac015ad38c4c61bcbf8dc7eac5cb",
 "actver":"0105aba61eb58ea2ac069f563999031cabf469fc",
 "src":"85f2a5de5885d158e08db6cceebf0e30cf5d5bb0",
 "srcver":"a0f46fe3b577c91686b1b8cc5b2436b35556a708",
 "overlay":"4e6a60814a097ef6905f487cadfe5e8264f2494a",
}
def blob(p):
 return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
 got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])
o={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
root,act,actver,src,srcver,overlay=o["root"],o["act"],o["actver"],o["src"],o["srcver"],o["overlay"]

assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
ctl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctl["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert ctl["fresh_reality_authority"] is False
assert ctl["external_fact_acquisition_overlay"]["activation_git_blob_sha"]==EXPECTED["overlay"]
assert ctl["external_fact_acquisition_overlay"]["low_value_support_waits"]==0

p=ctl["primary_source_search_deletions"]
assert p["activation_git_blob_sha"]==EXPECTED["act"]
assert p["activation_verification_git_blob_sha"]==EXPECTED["actver"]
assert p["source_refresh_git_blob_sha"]==EXPECTED["src"]
assert p["source_verification_git_blob_sha"]==EXPECTED["srcver"]
assert p["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__SCHEDULING_DELETIONS_ONLY__ZERO_CREDIT"
assert p["scheduler_deletion_count"]==6
assert p["fresh_reality_authority"] is False

expected_deleted={
 "HLE_EXISTENCE_AND_GENERIC_GATING_SEARCH",
 "CHARTOGRAPHY_GENERIC_FREE_TIER_AND_JUDGE_IDENTITY_SEARCH",
 "OSWORLD_V21_RELEASE_IDENTITY_108_TASK_AND_SELF_HOST_REQUIREMENT_SEARCH",
 "BUILDKITE_LARGE_AS_DURABLE_FREE_PLAN_CARRIER",
 "AUTOMATIONBENCH_PUBLIC600_PRIVATE_EQUIVALENCE_REPEAT_SEARCH",
 "CURSORBENCH_COMPARATOR_DRIFT_SEARCH_WHILE_CURRENT_OWNER_PAGE_REMAINS_57_8"
}
assert set(p["deleted"])==expected_deleted
assert set(act["delete"])==expected_deleted
assert actver["independent_runner"]["conclusion"]=="success"
assert actver["verified"]["scheduler_deletion_count"]==6
assert srcver["independent_runner"]["conclusion"]=="success"
assert set(srcver["scheduler_deletions_verified"])==expected_deleted

sched=root["scheduler_policy"]
assert sched["root2_primary_source_search_deletions"]=="canonical/governance/ROOT2_EXTERNAL_PRIMARY_SOURCE_REFRESH_ACTIVATION_V1.json"
assert sched["repeat_search_for_deleted_primary_source_classes_forbidden"] is True
assert sched["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True
assert sched["self_service_facts_are_owner_waits"] is False
assert sched["fresh_reality_before_zero_reality_fixed_point"] is False

assert root["accounting"]=={
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,
 "new_reality_units_consumed":0,"incremental_spend_usd":0
}
print("PASS: six independently verified primary-source search deletions are bound into canonical scheduling")
print("PASS: active Root2 V8 and external-fact acquisition overlay are preserved")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved preserved")
print("PASS: zero credit, zero spend, no fresh-reality authority")
