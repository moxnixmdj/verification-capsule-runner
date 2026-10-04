import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text(encoding="utf-8"))

root3=load("ROOT3_RESIDUAL_COMPRESSION_V1.json")
root=load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
vec=load("ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json")
rb=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V3.json")
cut=load("CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
front=load("ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
term=load("CURRENT_TERMINAL_AUTHORITY_V1.json")
routes=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
syn=load("SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osw=load("OSWORLD_V21_GITLAB_PROTOCOL_THEOREM_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

assert syn["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__SYNTHESIS_ROOT2_AND_ROOT3_TO_ROOT2_ONLY")
assert osw["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
p=root["current_residual_root_partition"]
assert p["unresolved_total"]==26
assert (p["root2_only_count"],p["root3_only_count"],p["root2_and_root3_count"])==(16,7,3)
assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in p["root2_only"]
assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" not in p["root2_and_root3"]
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["proved_atomic"]==12
assert root["root3_current_execution_state"]["live_root3_predicates"]==10

srows={x["predicate_id"]:x for x in root3["compressed_residuals"]}
s=srows["SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
assert s["root_class"]=="ROOT2"
assert s["scope_relation_closed"] is True
assert s["current_residual"]["missing_scope_relation"] is False
assert s["current_residual"]["missing_atoms"]==["metric:matched_quality"]
assert s["current_residual"]["missing_metric_bounds"]==["matched_quality_noninferiority","required_claim_coverage_noninferiority"]

assert routes["deduplication"]["root2_only_predicate_count"]==15
assert routes["deduplication"]["unique_benchmark_surface_count"]==14
osrow={x["surface"]:x for x in routes["routes"]}["OSWorld 2.1 partial"]
assert osrow["source_boundary_v1"]["gitlab_exact_revision_required"] is False
assert osrow["source_boundary_v1"]["gitlab_protocol_requirement"]=="FUNCTIONAL_REACHABILITY_VALID_TOKEN_AND_PROTOCOL_PREFLIGHT"
assert osrow["gitlab_protocol_reconciliation"]["removed"]=="GITLAB_EXACT_REVISION_OR_INDEPENDENT_EQUIVALENCE_BINDING"

assert vec["authority"]["route_inventory_git_blob_sha"]=="71495ebcf456119f4df694203631aeeb3048c81a"
assert vec["semantic_delta"]["comparator_targets_changed"] is False
assert len(vec["surfaces"])==14
assert sum(len(x["predicates"]) for x in vec["surfaces"])==15
assert rb["current_inputs"]["route_inventory_git_blob_sha"]=="71495ebcf456119f4df694203631aeeb3048c81a"
assert rb["current_inputs"]["comparator_vector_git_blob_sha"]=="f426f1aa136abdcc33a14716fe4edbc40003bf2a"
assert rb["invariants"]["total_root2_involved_predicates_after_synthesis_reclassification"]==19
assert rb["fresh_reality_authority"] is False

e=cut["exact_state"]
assert (e["accepted_families"],e["proved_atomic"],e["unresolved_atomic"])==(5,12,26)
assert (e["root2_only_count"],e["root3_only_count"],e["root2_and_root3_count"])==(16,7,3)
assert cut["authority"]["root2_routes"]["git_blob_sha"]=="71495ebcf456119f4df694203631aeeb3048c81a"
assert cut["fresh_reality_authority"] is False
assert cut["incremental_spend_usd"]==0
assert cut["terminal_cases_consumed"]==0

f=front["exact_state"]
assert (f["root2_only_count"],f["root3_only_count"],f["root2_and_root3_count"])==(16,7,3)
assert front["root2_non_fixed_bar_residual"]["predicate_id"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert front["root2_non_fixed_bar_residual"]["scope_relation_closed"] is True
assert front["fresh_reality_authority"] is False

assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False
assert "19_PREDICATES_TOUCH_ROOT2" in term["next_terminal_action"]
assert "FIXED_BAR_HYPERGRAPH_CURRENT_REBIND_PENDING_VERIFICATION" in term["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_CURRENT_STATE_V4_PUBLIC_RUNNER_RESULT",
 "status":"PASS__16_ROOT2_ONLY__7_ROOT3_ONLY__3_MIXED__19_TOUCH_ROOT2__OSWORLD_GITLAB_REVISION_DELETED__SYNTHESIS_SCOPE_CLOSED__FIXED_BAR_REBIND_SOUND__ZERO_CREDIT",
 "accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,
 "root2_only":16,"root2_and_root3":3,"root2_involved":19,
 "terminal_cases_consumed":0,"incremental_spend_usd":0,
 "fresh_reality_authority":False,"promotion_authority":False
},sort_keys=True))
