#!/usr/bin/env python3
import json
from pathlib import Path

R=Path(__file__).resolve().parent
def J(name): return json.loads((R/name).read_text())

p=J("TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2.json")
root=J("ADAPTIVE_V2_TERMINAL_ROOT_CAUSE_STATE_V1.json")
r2=J("ADAPTIVE_V2_ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1.json")
r3=J("ADAPTIVE_V2_ROOT3_MINIMUM_ACTION_CUT_V2.json")
ret=J("ADAPTIVE_V2_GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json")

assert p["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2"
assert p["compiled_from_main"]=="eaaa39503d6daf3fb2761c3b79a6dfb0bd2aa1a6"
assert p["exact_live_state"]["accepted_families"]==5
assert p["exact_live_state"]["open_families"]==14
assert p["exact_live_state"]["proved_atomic"]==12
assert p["exact_live_state"]["unresolved_atomic"]==26
assert p["exact_live_state"]["root1_positive_gaps"]==0
assert p["execution_authority"] is False
assert p["promotion_authority"] is False
assert p["fresh_reality_authority"] is False
assert p["accounting"]["incremental_spend_usd"]==0
assert p["accounting"]["terminal_cases_consumed"]==0

rb=p["authority_bindings"]["root2"]
assert rb["frontier_git_blob_sha"]=="2012926814d0d06405da56da64e589b06fef1756"
assert rb["final_activation_git_blob_sha"]=="f5eda02fcc104bc8a5e13a82bfc8ec3d9515dcb2"
assert rb["effective_scheduling_authority"] is True
assert rb["execution_authority"] is False
assert rb["fresh_reality_authority"] is False
assert (rb["self_service_fact_count"],rb["owner_exclusive_fact_count"],rb["owner_or_direct_platform_receipt_count"],rb["dormant_fact_count"])==(9,6,1,2)
assert rb["low_value_support_waits"]==0

ac=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ac["current_frontier_path"]==rb["frontier_path"]
assert ac["current_frontier_git_blob_sha"]==rb["frontier_git_blob_sha"]
assert ac["current_frontier_activation_path"]==rb["final_activation_path"]
assert ac["current_frontier_activation_git_blob_sha"]==rb["final_activation_git_blob_sha"]
assert ac["effective_scheduling_authority"] is True
ov=ac["external_fact_acquisition_overlay"]
assert (ov["self_service_fact_count"],ov["owner_exclusive_fact_count"],ov["owner_or_direct_platform_receipt_count"],ov["dormant_fact_count"])==(9,6,1,2)
assert ov["low_value_support_waits"]==0

assert r2["schema"]=="PROJECT_BRAIN_ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1"
assert r2["authority"]["effective_scheduling"] is True
assert r2["authority"]["execution"] is False
assert r2["authority"]["promotion"] is False
assert r2["authority"]["fresh_reality"] is False

r3b=p["authority_bindings"]["root3"]
assert r3b["cut_git_blob_sha"]=="4d8ce78ebe312100bbfc524062199961c0c6479d"
assert r3["live_root3_predicates"]==10
assert r3["matched_scope_targets"]==7
assert r3["event_class_count"]==3
assert r3["currently_runnable_event_count"]==0
assert r3["fresh_reality_authority"] is False

retb=p["authority_bindings"]["retrieval"]
assert retb["current_authority_git_blob_sha"]=="55b1d411561f720fcd9d66c127cecd63ef0b5f5e"
assert retb["mandatory_entrypoint"]=="canonical/runtime/global_retrieval_entrypoint_v4.py"
assert retb["mandatory_entrypoint_git_blob_sha"]=="2ad2fb952b3c361e74cb083b335d39b04a7c130b"
assert ret["v19_verified_route_portfolio"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert ret["v19_verified_route_portfolio"]["entrypoint_v4_git_blob_sha"]==retb["mandatory_entrypoint_git_blob_sha"]

assert set(p["preserved_search_deletions"])==set(ac["primary_source_search_deletions"]["deleted"])
assert any(x["phase"]=="FRESH_REALITY" and x["action"]=="BLOCKED" for x in p["current_execution_policy"])
assert "NO INVENTED POINT PROBABILITIES" in p["hard_rules"]
assert "UNKNOWN IS NOT MISSING" in p["hard_rules"]

print(json.dumps({
 "status":"PASS",
 "policy":"V2",
 "root2":"V10_ACTIVE",
 "root3":"V2_ZERO_RUNNABLE",
 "retrieval":"V19_ENTRYPOINT_V4",
 "acceptance":"5/19",
 "atomic":"12/38",
 "fresh_reality":False,
 "zero_spend":True
},sort_keys=True))
