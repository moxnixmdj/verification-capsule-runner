import json, pathlib, subprocess

FILES={
 "v7":"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V7.json",
 "v6":"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json",
 "guard":"canonical/governance/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_V1.json",
 "guardv":"canonical/verification/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "adapter":"canonical/governance/FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_V1.json",
 "adapterv":"canonical/verification/FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "root":"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
}
EXPECTED={
 "v7":"35e8b578aca1290bcf469d6350ae085ba8a86c64",
 "v6":"fcbdb818b63b4986b026db29c400a47373a26fdb",
 "guard":"278a3317564138088fd8af83a8734a84fe09b158",
 "guardv":"342740561634a86d0c55876ee126e8122b21af0f",
 "adapter":"280fc9b41221f6b4fa58ac50b18a0a4d6fceb5ec",
 "adapterv":"31ed06c9469c9a915108ac970b4790a5f5f77e75",
 "root":"78f70dc63654b7d4be0917fce9405088177a48b5",
}
def blob(p):
 return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
def load(k): return json.loads(pathlib.Path(FILES[k]).read_text())
for k,p in FILES.items():
 g=blob(p); assert g==EXPECTED[k],(k,g,EXPECTED[k])

v7=load("v7"); v6=load("v6"); guard=load("guard"); guardv=load("guardv")
adapter=load("adapter"); adapterv=load("adapterv"); root=load("root")

assert v7["supersedes_for_scheduling_if_verified"]==FILES["v6"]
assert v7["source_bindings"]["prior_frontier_v6"]["git_blob_sha"]==EXPECTED["v6"]
assert v7["exact_state"]==v6["exact_state"]
assert v7["exact_state"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "root1_positive_gap_count":0,"root2_only_count":16,"root3_only_count":7,
 "root2_and_root3_count":3,"root2_touching_predicates":19
}

assert guardv["independent_runner"]["conclusion"]=="success"
assert adapterv["verifier"]["conclusion"]=="success"
assert adapterv["subject"]["governance"]["git_blob_sha"]==EXPECTED["adapter"]
assert guard["current_evidence"]["scored_task_executions"]==1350

deltas=v7["projection_deltas"]
finance=[x for x in deltas if x["target"]=="FINANCE_AGENT_V2_GE_58_59"]
assert any(x.get("deletion")=="A_PRIORI_WORST_CASE_PROVIDER_DEMAND_PROOFS_AS_EXECUTION_PRECONDITION" for x in finance)
assert v7["finance_agent_v2_zero_spend_route"]["provider_call_interception"]=="VERIFIED_RETRY_SAFE"
assert v7["finance_agent_v2_zero_spend_route"]["a_priori_worst_case_provider_demand_proof_required"] is False
assert v7["finance_agent_v2_zero_spend_route"]["scored_task_executions"]==1350
assert set(v7["finance_agent_v2_zero_spend_route"]["remaining_zero_reality"])=={
 "VALS_PLATFORM_APPROVAL","EXACT_OFFICIAL_TEST_SUITE_ID",
 "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TAVILY","CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_SEC_API",
 "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TIINGO","ZERO_COST_OUTCOME_TELEMETRY_BINDING"
}

assert "NO_FINANCE_AGENT_V2_A_PRIORI_WORST_CASE_PROVIDER_DEMAND_PROOF_REQUIRED_AFTER_VERIFIED_GUARD_AND_ADAPTER" in v7["hard_rules"]
assert v7["execution_authority"] is False
assert v7["promotion_authority"] is False
assert v7["fresh_reality_authority"] is False
for k,v in v7["accounting"].items():
 if k.endswith("_delta") or k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed"):
  assert v==0,(k,v)

# Current authority is V6 before this projection is activated. This is expected.
ctrl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctrl["current_frontier_git_blob_sha"]==EXPECTED["v6"]
assert ctrl["effective_scheduling_authority"] is True
assert ctrl["fresh_reality_authority"] is False

print("PASS__ROOT2_V7_FINANCE_ZERO_SPEND_COMPRESSION__COUNTS_STABLE__ZERO_CREDIT__NO_FRESH_REALITY")
