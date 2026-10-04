import json, pathlib, subprocess

FILES = {
    "v5": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json",
    "receipt": "subject/ROOT2_V5_COMPONENT_TRUTH_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "v4": "subject/CURRENT_MAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json",
    "circleci": "subject/TB4_CIRCLECI_FREE_XLARGE_CONTRADICTION_RECONCILIATION_20261004_V1.json",
    "vals": "subject/FINANCE_AGENT_V2_PUBLIC_RUNNER_ROUTE_RECONCILIATION_20261004_V1.json",
}
EXPECTED = {
    "v5": "e948022f0a4e8d91b949a5155d850d56aa137c87",
    "receipt": "0f0e8632425e32a1f446291b5536843b07545255",
    "v4": "8c90a1dc4903f9b895788ff2864822d6ebc26ac9",
    "circleci": "0c5d16da02e7a71c5583f7c1a743adf389fc47b1",
    "vals": "126ff389982aab89f810388b1adbe402c25a7a59",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()
for k,p in FILES.items():
    got=blob(p); assert got==EXPECTED[k], (k,got,EXPECTED[k])

v5=json.loads(pathlib.Path(FILES["v5"]).read_text())
v4=json.loads(pathlib.Path(FILES["v4"]).read_text())
receipt=json.loads(pathlib.Path(FILES["receipt"]).read_text())
circleci=json.loads(pathlib.Path(FILES["circleci"]).read_text())
vals=json.loads(pathlib.Path(FILES["vals"]).read_text())

assert v5["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json"
assert v5["source_bindings"]["prior_frontier_v4"]["git_blob_sha"]==EXPECTED["v4"]
assert v5["source_bindings"]["component_verification"]["git_blob_sha"]==EXPECTED["receipt"]
assert v5["source_bindings"]["circleci_truth_repair"]["git_blob_sha"]==EXPECTED["circleci"]
assert v5["source_bindings"]["finance_agent_v2_route"]["git_blob_sha"]==EXPECTED["vals"]

expected_state={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "root1_positive_gap_count":0,"root2_only_count":16,"root3_only_count":7,
 "root2_and_root3_count":3,"root2_touching_predicates":19,
}
assert v5["exact_state"]==expected_state

# Projection must preserve all unaffected V4 semantic classes while applying only the verified deltas.
assert v4["root2_touching_predicates"]==19
assert receipt["independent_verifier"]["pull_request"]==1566
assert receipt["independent_verifier"]["merge_commit"]=="f59ed70eee74b6ff351e401c4314cf8e6ea6532e"
assert receipt["independent_verifier"]["workflow_run_id"]==37168128393
assert receipt["independent_verifier"]["workflow_job_id"]==111335299373
assert receipt["independent_verifier"]["conclusion"]=="success"
assert receipt["verified"]["circleci_live_pricing_xlarge_free"] is False
assert receipt["verified"]["vals_custom_model_or_harness_hook_exists"] is True
assert receipt["verified"]["zero_terminal_credit_preserved"] is True

providers=[x["provider"] for x in v5["tb4_carrier_portfolio"]["candidates"]]
assert providers==["Buildkite"], providers
deleted={x["provider"]:x["reason"] for x in v5["tb4_carrier_portfolio"]["deleted"]}
assert "CircleCI" in deleted and "8_VCPU" in deleted["CircleCI"]
assert circleci["conclusion"]["current_circleci_free_xlarge_route_killed"] is True
assert circleci["conclusion"]["documented_free_route_meets_tb4_8cpu_envelope"] is False

assert any(x.startswith("FINANCE_AGENT_V2_VALS_PLATFORM_APPROVAL") for x in v5["runnable_zero_reality"])
assert "VALS_PLATFORM_FINANCE_AGENT_V2_APPROVAL_AND_EXACT_SUITE_ID" in v5["waiting_external_facts"]
assert "FINANCE_AGENT_V2_ZERO_COST_TOOL_DEPENDENCY_READINESS" in v5["waiting_external_facts"]
assert "VALS_MYSTERYMECHANISM_OWNER_OR_EXACT_ROUTE_RESULT" in v5["waiting_external_facts"]
assert vals["route_reduction"]["owner_run_receipt_remains_valid_alternative"] is True
assert "BRAIN_SCORE_GE_58_59" in vals["not_proved"]

for obj in (v5, receipt, circleci, vals):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False
    acct=obj["accounting"]
    for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed",
              "acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        assert acct[k]==0, (obj["schema"],k,acct[k])

assert "MATCHED_SUPERPORTFOLIO_EMPIRICAL_WAVE" in v5["fresh_reality_preserved_not_authorized"]
assert "ROOT3_DIRECT_ORACLE_RESIDUAL" in v5["fresh_reality_preserved_not_authorized"]

print("PASS: current-main Root2 V4 -> verified V5 projection")
print("PASS: CircleCI Free X-large deleted; Buildkite preserved")
print("PASS: Finance Agent v2 public runner bound; gated suite/access/tool-dependency residuals preserved")
print("PASS: 5/19 accepted, 12/38 proved, 26 unresolved; zero credit; no fresh reality")
