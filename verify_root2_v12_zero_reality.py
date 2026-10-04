#!/usr/bin/env python3
import json, pathlib, subprocess

BASE=pathlib.Path("subject/root2_v12_zero_reality_20261004_sol")
P11=BASE/"V11.json"; P12=BASE/"V12.json"
H11="6857750dea3a0af48a5acc545b6f66b619d4335b"
H12="75ca9127a73ca2dd52a49f2f09e2e0ccc384129a"

def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()

assert blob(P11)==H11,(blob(P11),H11)
assert blob(P12)==H12,(blob(P12),H12)
a=json.loads(P11.read_text()); b=json.loads(P12.read_text())

assert a["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11"
assert b["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12"
assert b["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json"

for k in (
    "exact_state","causal_action_order","waiting_external_facts",
    "fresh_reality_preserved_not_authorized","probability_policy",
    "tb4_carrier_portfolio","finance_agent_v2_zero_spend_route",
    "finance_agent_v2_dual_route","composition_provenance",
):
    assert a[k]==b[k],k

for k in a["source_bindings"]:
    assert b["source_bindings"][k]==a["source_bindings"][k],f"source drift:{k}"

rel=b["source_bindings"]["relative_elo_nontransport"]
assert rel["activation_git_blob_sha"]=="5edaf436becf45c8d8f3477ac7a53a1e8ac3a63a"
assert rel["verification_git_blob_sha"]=="b6daf8b1892a8dc11020b6c5a4102b1fed256240"
syn=b["source_bindings"]["synthesis_dimension_scorers_and_strict_reducer"]
assert syn["activation_git_blob_sha"]=="300fb663e6b598b389961ddf663d88abcd206545"
assert syn["verification_git_blob_sha"]=="e13360b7aba2756f0eb97cac977515c07f3bcbdc"
assert b["source_bindings"]["combined_root_projection"]["git_blob_sha"]=="9ac3c636b2ed76c7f4b1c7cfd8e2762bc7230d0c"

assert b["projection_deltas"][:len(a["projection_deltas"])]==a["projection_deltas"]
new=b["projection_deltas"][len(a["projection_deltas"]):]
assert len(new)==2
assert any("PROWORK_GDPVAL_GE_1846" in x["target"] and x["deletion"]=="PURE_ABSOLUTE_NON_RELATIVE_PROOF_FORMS_AS_SUFFICIENT_FIXED_ELO_ROUTES" for x in new)
assert any(x["target"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" and x["deletion"]=="FIVE_DIMENSION_SCORER_BINDINGS_AND_CONSERVATIVE_NONINFERIORITY_REDUCER_UNDERSPECIFIED" for x in new)

expected=[x for x in a["runnable_zero_reality"] if x not in {
    "GDPVAL_EXACT_PAIRWISE_ROUTE_OR_STRONGER_PROOF",
    "SYNTHESIS_MATCHED_QUALITY_METRIC_AND_NONINFERIORITY_ONLY",
}]
expected += [
    "GDPVAL_AND_AA_BRIEFCASE_RELATIVE_SCORE_BRIDGE_OR_EXISTING_COMPARATOR_OR_OWNER_RESULT_ONLY__PURE_ABSOLUTE_NON_RELATIVE_ROUTES_PRUNED",
    "SYNTHESIS_EXACT_OPUS55_COMPARATOR_OR_SEPARATELY_VERIFIED_STRONGER_PROOF_ONLY__SCORERS_AND_STRICT_REDUCER_FROZEN__MATCHED_RESULT_REMAINS_FRESH_REALITY_BLOCKED",
]
assert b["runnable_zero_reality"]==expected

assert b["exhausted_or_deleted"][:len(a["exhausted_or_deleted"])]==a["exhausted_or_deleted"]
assert len(b["exhausted_or_deleted"])==len(a["exhausted_or_deleted"])+2
assert b["hard_rules"][:len(a["hard_rules"])]==a["hard_rules"]
assert len(b["hard_rules"])==len(a["hard_rules"])+2

assert b["accounting"]=={
    "incremental_spend_usd":0,"new_reality_units_consumed":0,
    "terminal_cases_consumed":0,"acceptance_credit_delta":0,
    "family_credit_delta":0,"capability_credit_delta":0,
    "ownership_credit_delta":0,
}
assert b["execution_authority"] is False
assert b["promotion_authority"] is False
assert b["fresh_reality_authority"] is False
assert b["exact_state"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,
    "unresolved_atomic":26,"root1_positive_gap_count":0,
    "root2_only_count":16,"root3_only_count":7,
    "root2_and_root3_count":3,"root2_touching_predicates":19,
}
print("PASS: Root2 V12 is a pure zero-credit scheduling reduction over exact V11")
print("PASS: relative-Elo invalid route forms pruned only conditionally")
print("PASS: synthesis scorer/reducer underspecification deleted; comparator/result remain")
print("PASS: counts, external facts, fresh-reality block, and unrelated routes unchanged")
