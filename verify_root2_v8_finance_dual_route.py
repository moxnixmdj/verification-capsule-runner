import copy
import json
import pathlib
import subprocess

BASE="subject/root2_v8_finance_dual_20261004_sol"
FILES={
  "v6":f"{BASE}/V6.json",
  "v7":f"{BASE}/V7.json",
  "v8":f"{BASE}/V8.json",
  "custom":f"{BASE}/CUSTOM_ROUTE.json",
  "custom_ver":f"{BASE}/CUSTOM_ROUTE_VERIFICATION.json",
  "guard_ver":f"{BASE}/GUARD_VERIFICATION.json",
  "adapter_ver":f"{BASE}/ADAPTER_VERIFICATION.json",
}
EXPECTED={
  "v6":"fcbdb818b63b4986b026db29c400a47373a26fdb",
  "v7":"35e8b578aca1290bcf469d6350ae085ba8a86c64",
  "v8":"93375aded82379b21ba02f05d19d947921c54ac6",
  "custom":"79a60cb1c407fdabe68643ca91fcc2836ea000b1",
  "custom_ver":"01eeac7d1d096d7dcbb1e401e013d85d8d4aaaa3",
  "guard_ver":"342740561634a86d0c55876ee126e8122b21af0f",
  "adapter_ver":"31ed06c9469c9a915108ac970b4790a5f5f77e75",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

v6=json.loads(pathlib.Path(FILES["v6"]).read_text())
v7=json.loads(pathlib.Path(FILES["v7"]).read_text())
v8=json.loads(pathlib.Path(FILES["v8"]).read_text())
custom=json.loads(pathlib.Path(FILES["custom"]).read_text())
custom_ver=json.loads(pathlib.Path(FILES["custom_ver"]).read_text())
guard_ver=json.loads(pathlib.Path(FILES["guard_ver"]).read_text())
adapter_ver=json.loads(pathlib.Path(FILES["adapter_ver"]).read_text())

# Frozen terminal accounting cannot move.
assert v6["exact_state"]==v7["exact_state"]==v8["exact_state"]=={
  "accepted_families":5,
  "open_families":14,
  "proved_atomic":12,
  "unresolved_atomic":26,
  "root1_positive_gap_count":0,
  "root2_only_count":16,
  "root3_only_count":7,
  "root2_and_root3_count":3,
  "root2_touching_predicates":19,
}
assert v6["accounting"]==v7["accounting"]==v8["accounting"]=={
  "incremental_spend_usd":0,
  "new_reality_units_consumed":0,
  "terminal_cases_consumed":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
}
for obj in (v6,v7,v8,custom,custom_ver):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

# First prove the V6 -> V7 default-route compression directly from independently verified components.
v6d={(x["target"],x["deletion"]):x for x in v6["projection_deltas"]}
v7d={(x["target"],x["deletion"]):x for x in v7["projection_deltas"]}
for key,val in v6d.items():
    assert key in v7d and v7d[key]==val, key
v7_extra=[x for x in v7["projection_deltas"] if (x["target"],x["deletion"]) not in v6d]
assert len(v7_extra)==1, v7_extra
assert v7_extra[0]["target"]=="FINANCE_AGENT_V2_GE_58_59"
assert v7_extra[0]["deletion"]=="A_PRIORI_WORST_CASE_PROVIDER_DEMAND_PROOFS_AS_EXECUTION_PRECONDITION"
assert guard_ver["verifier"]["conclusion"]=="success"
assert adapter_ver["verifier"]["conclusion"]=="success"
assert "NO_FREE_QUOTA_SUFFICIENCY_CLAIM" in adapter_ver["hard_nonclaims"]
assert "NO_CURRENT_PROVIDER_ACCOUNT_OR_KEY_CLAIM" in adapter_ver["hard_nonclaims"]

# Then prove V7 -> V8 adds exactly the verified conditional custom route, not a benchmark shortcut.
v8d={(x["target"],x["deletion"]):x for x in v8["projection_deltas"]}
for key,val in v7d.items():
    assert key in v8d and v8d[key]==val, key
v8_extra=[x for x in v8["projection_deltas"] if (x["target"],x["deletion"]) not in v7d]
assert len(v8_extra)==1, v8_extra
extra=v8_extra[0]
assert extra["target"]=="FINANCE_AGENT_V2_GE_58_59"
assert extra["deletion"]=="DEFAULT_TAVILY_SEC_API_TIINGO_STACK_AS_UNIQUE_TECHNICAL_VALS_SUITE_EXECUTION_ROUTE"
assert "COMPARABILITY" in extra["reason"]

assert v8["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert v8["subsumes_unactivated_candidate"]["git_blob_sha"]==EXPECTED["v7"]
src=v8["source_bindings"]["finance_agent_v2_custom_function_alternative_route"]
assert src["git_blob_sha"]==EXPECTED["custom"]
assert src["verification_git_blob_sha"]==EXPECTED["custom_ver"]

# Custom route independent proof says existence only; comparator equivalence and platform zero-spend remain open.
assert custom_ver["independent_verifier"]["conclusion"]=="success"
assert "CUSTOM_FUNCTION_EXISTENCE_ALONE_DOES_NOT_PROVE_COMPARABILITY" in custom_ver["verified"]
assert "DEFAULT_HARNESS_ROUTE_REMAINS_OPEN" in custom_ver["verified"]
assert "CUSTOM_FUNCTION_ROUTE_IS_CONDITIONAL_ON_COMPARABILITY_AND_PLATFORM_ZERO_SPEND" in custom_ver["verified"]
assert "NO_CLAIM_CUSTOM_FUNCTION_SCORE_IS_CURRENTLY_COMPARABLE" in custom_ver["hard_nonclaims"]
assert "NO_CLAIM_VALS_PLATFORM_EXECUTION_IS_FREE" in custom_ver["hard_nonclaims"]
assert "NO_CLAIM_DEFAULT_TOOL_PROVIDER_QUOTAS_ARE_DELETED" in custom_ver["hard_nonclaims"]

default=custom["route_graph"]["default_harness_route"]
alt=custom["route_graph"]["custom_function_route"]
assert default["state"]=="OPEN"
assert alt["state"]=="CONDITIONALLY_OPEN"
assert "CUSTOM_FUNCTION_OR_CUSTOM_HARNESS_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS_VERIFIED" in alt["requires"]
assert "VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_RECEIPT_OR_OWNER_NO_COST_ROUTE" in alt["requires"]

# V8 must keep both routes and explicitly prohibit cross-harness score blending.
dual=v8["finance_agent_v2_dual_route"]
assert dual["default_shared_harness"]["state"]=="OPEN__ZERO_SPEND_GUARD_AND_RETRY_SAFE_ADAPTER_VERIFIED"
assert dual["custom_function"]["state"]=="CONDITIONALLY_OPEN__ROUTE_EXISTENCE_INDEPENDENTLY_VERIFIED"
assert dual["route_selection_rule"]=="PROMOTE_FIRST_FULLY_ADMISSIBLE_ZERO_INCREMENTAL_SPEND_COMPARABLE_ROUTE__DO_NOT_MERGE_SCORE_EVIDENCE_ACROSS_NONCOMPARABLE_HARNESSES"
for req in (
    "CUSTOM_FUNCTION_OR_CUSTOM_HARNESS_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS_VERIFIED",
    "VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_RECEIPT_OR_OWNER_NO_COST_ROUTE",
):
    assert req in dual["custom_function"]["requires"]

# Provider requirements remain mandatory on the default branch and merely conditional-deletable on the alternative branch.
for req in (
    "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TAVILY",
    "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_SEC_API",
    "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TIINGO",
    "ZERO_COST_OUTCOME_TELEMETRY_BINDING",
):
    assert req in dual["default_shared_harness"]["requires"]
assert "FINANCE_AGENT_V2_CUSTOM_FUNCTION_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS" in v8["waiting_external_facts"]
assert "FINANCE_AGENT_V2_VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_ROUTE" in v8["waiting_external_facts"]

for rule in (
    "NO_FINANCE_AGENT_V2_CUSTOM_FUNCTION_SCORE_COMPARABILITY_INFERENCE_FROM_GENERIC_VALS_SDK_SUPPORT_ALONE",
    "NO_FINANCE_AGENT_V2_DEFAULT_PROVIDER_QUOTA_ROUTE_DELETION_UNTIL_CUSTOM_FUNCTION_COMPARABILITY_IS_VERIFIED",
    "NO_FINANCE_AGENT_V2_VALS_PLATFORM_OR_JURY_ZERO_SPEND_ASSUMPTION_WITHOUT_RECEIPT_OR_OWNER_CONFIRMATION",
):
    assert rule in v8["hard_rules"]

# Root3 and fresh-reality gates must remain blocked exactly as inherited.
assert v8["fresh_reality_preserved_not_authorized"]==v7["fresh_reality_preserved_not_authorized"]
assert "MATCHED_SUPERPORTFOLIO_EMPIRICAL_WAVE" in v8["fresh_reality_preserved_not_authorized"]
assert "ROOT3_DIRECT_ORACLE_RESIDUAL" in v8["fresh_reality_preserved_not_authorized"]

# Aside from the explicitly permitted V8 fields, the V7 projection is unchanged.
norm=copy.deepcopy(v8)
norm["schema"]=v7["schema"]
norm["status"]=v7["status"]
norm["supersedes_for_scheduling_if_verified"]=v7["supersedes_for_scheduling_if_verified"]
norm.pop("subsumes_unactivated_candidate",None)
norm["source_bindings"].pop("prior_frontier_v7_candidate",None)
norm["source_bindings"].pop("finance_agent_v2_custom_function_alternative_route",None)
norm["projection_deltas"]=v7["projection_deltas"]
norm["runnable_zero_reality"]=v7["runnable_zero_reality"]
norm["waiting_external_facts"]=v7["waiting_external_facts"]
norm["hard_rules"]=v7["hard_rules"]
norm.pop("finance_agent_v2_dual_route",None)
assert norm==v7, "V8 contains semantic drift outside the admitted dual-route delta"

print("PASS: active V6 -> V8 projection is exactly V7 verified default-route compression plus one verified conditional custom route")
print("PASS: default-harness zero-spend guard/adapter preserved")
print("PASS: custom route exists but comparability and Vals platform/jury zero-spend remain open")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved; zero credit; no fresh reality")
