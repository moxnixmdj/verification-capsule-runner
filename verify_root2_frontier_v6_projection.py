import json, pathlib, subprocess

BASE="subject/root2_v6_20261004_sol"
FILES={
 "v5":f"{BASE}/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json",
 "v6":f"{BASE}/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json",
 "fi_act":f"{BASE}/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
 "fi_ver":f"{BASE}/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "fa_mass":f"{BASE}/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_REDUCTION_20261004_V1.json",
 "fa_ver":f"{BASE}/FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}
EXPECTED={
 "v5":"e948022f0a4e8d91b949a5155d850d56aa137c87",
 "v6":"fcbdb818b63b4986b026db29c400a47373a26fdb",
 "fi_act":"9b9d4a41d19a5e58e8967027e1d1837790287dc2",
 "fi_ver":"f7c1127834aee3c70dc4634e8273e3a887e45c66",
 "fa_mass":"ec36936e92a6111aed6b1813a45225fb4ca867dc",
 "fa_ver":"cbdc6b3e773e86a1e57e119a6dd2c690ee1c6b11",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p); assert got==EXPECTED[k], (k,got,EXPECTED[k])

v5=json.loads(pathlib.Path(FILES["v5"]).read_text())
v6=json.loads(pathlib.Path(FILES["v6"]).read_text())
fia=json.loads(pathlib.Path(FILES["fi_act"]).read_text())
fiv=json.loads(pathlib.Path(FILES["fi_ver"]).read_text())
fam=json.loads(pathlib.Path(FILES["fa_mass"]).read_text())
fav=json.loads(pathlib.Path(FILES["fa_ver"]).read_text())

assert v6["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
assert v6["source_bindings"]["prior_frontier_v5"]["git_blob_sha"]==EXPECTED["v5"]
assert v6["source_bindings"]["finance_index_direct_threshold_activation"]["git_blob_sha"]==EXPECTED["fi_act"]
assert v6["source_bindings"]["finance_index_direct_threshold_activation"]["verification_git_blob_sha"]==EXPECTED["fi_ver"]
assert v6["source_bindings"]["finance_agent_v2_heldout_mass"]["git_blob_sha"]==EXPECTED["fa_mass"]
assert v6["source_bindings"]["finance_agent_v2_heldout_mass"]["verification_git_blob_sha"]==EXPECTED["fa_ver"]

assert v6["exact_state"]==v5["exact_state"]
assert v6["tb4_carrier_portfolio"]==v5["tb4_carrier_portfolio"]
assert v6["accounting"]==v5["accounting"]=={
 "incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0
}
for obj in (v6,fiv,fam,fav):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False
assert fia["authority"]["execution_authority"] is False
assert fia["authority"]["promotion_authority"] is False
assert fia["authority"]["fresh_reality_authority"] is False

v5d={(x["target"],x["deletion"]):x for x in v5["projection_deltas"]}
v6d={(x["target"],x["deletion"]):x for x in v6["projection_deltas"]}
for k,x in v5d.items():
    assert k in v6d and v6d[k]==x, k

extra=[x for x in v6["projection_deltas"] if (x["target"],x["deletion"]) not in v5d]
assert len(extra)==2, extra
keys={(x["target"],x["deletion"]) for x in extra}
assert keys=={
 ("FINANCE_ACCOUNTING_INDEX_GE_61","COMPONENTWISE_OPUS_NONINFERIORITY_AS_MANDATORY_ROUTE"),
 ("FINANCE_AGENT_V2_GE_58_59","OFFICIAL_HELDOUT_SUITE_SIZE_UNKNOWN"),
}

s=fia["scheduling_effect"]
assert s["new_primary_route"]=="MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert s["exact_rule"]=="SUM_i(w_i*VERIFIED_BRAIN_LOWER_BOUND_i)>=61"
assert s["componentwise_opus_noninferiority"]=="RETAIN_AS_SUFFICIENT_FALLBACK_NOT_MANDATORY"
assert s["default_component_floors_allowed"] is False
assert s["separate_index_run_required"] is False
assert fiv["independent_runner"]["conclusion"]=="success"
assert fiv["verified"]["weighted_deficit_route_is_scheduling_only"] is True
assert fiv["verified"]["accepted_families"]==5
assert fiv["verified"]["proved_atomic"]==12
assert fiv["verified"]["unresolved_atomic"]==26

assert fam["derived"]["heldout_questions_per_run"]==450
assert fam["derived"]["runs_per_model"]==3
assert fam["derived"]["scored_task_executions"]==1350
assert "OFFICIAL_HELDOUT_SUITE_SIZE_UNKNOWN" in fam["delete_as_blocker"]
assert "VALS_PLATFORM_APPROVAL" in fam["preserve"]
assert "EXACT_OFFICIAL_TEST_SUITE_ID" in fam["preserve"]
assert "WORST_CASE_OR_EMPIRICAL_TAVILY_USAGE_WITHIN_FREE_CREDITS" in fam["preserve"]
assert "WORST_CASE_OR_EMPIRICAL_SEC_API_USAGE_WITHIN_100_FREE_CALLS" in fam["preserve"]
assert "WORST_CASE_OR_EMPIRICAL_TIINGO_USAGE_WITHIN_STARTER_LIMITS" in fam["preserve"]
assert fav["independent_runner"]["conclusion"]=="success"
assert fav["verified"]["heldout_test_questions_per_run"]==450
assert fav["verified"]["runs_per_model"]==3
assert fav["verified"]["scored_task_executions"]==1350
assert fav["verified"]["official_heldout_suite_size_unknown_deleted"] is True

assert "FINANCE_AGENT_V2_1350_EXECUTION_TAVILY_SEC_API_TIINGO_FREE_USAGE_FEASIBILITY" in v6["waiting_external_facts"]
assert "VALS_PLATFORM_FINANCE_AGENT_V2_APPROVAL_AND_EXACT_SUITE_ID" in v6["waiting_external_facts"]
assert "NO_FINANCE_AGENT_V2_SCORE_EXECUTION_BEFORE_EXACT_SUITE_AND_ZERO_COST_TOOL_DEPENDENCIES_ARE_BOUND" in v6["hard_rules"]
assert "NO_FINANCE_AGENT_V2_FREE_QUOTA_SUFFICIENCY_INFERENCE_FROM_1350_EXECUTION_MASS_ALONE" in v6["hard_rules"]

print("PASS: Root2 V5 -> V6 projection exact")
print("PASS: Finance Index route compressed to weighted verified lower bound >= 61")
print("PASS: Finance Agent v2 execution mass fixed at 450 x 3 = 1350 without quota sufficiency inference")
print("PASS: 5/19 accepted, 12/38 proved, 26 unresolved; zero credit; no fresh reality")
