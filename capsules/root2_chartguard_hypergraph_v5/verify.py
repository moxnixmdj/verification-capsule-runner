import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())
g=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_V1.json")
gv=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
ga=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_ACTIVATION_V1.json")
routes=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
vec=load("ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json")
rb=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V4.json")
cut=load("CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
front=load("ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
term=load("CURRENT_TERMINAL_AUTHORITY_V1.json")

assert gv["independent_runner"]["workflow_run_id"]==37163725050
assert gv["independent_runner"]["conclusion"]=="success"
assert ga["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert ga["independent_verification"]["git_blob_sha"]=="d2eb956d6534bd4748010ee3fec8b12d93795793"
r={x["surface"]:x for x in routes["routes"]}
c=r["Chartography with tools"]
assert "HARD_ZERO_SPEND_GUARD_INDEPENDENTLY_VERIFIED" in c["state"]
assert c["zero_spend_guard"]["status"]=="ACTIVE__INDEPENDENTLY_VERIFIED"
assert c["zero_spend_guard"]["remaining"]==["PROJECT_SPECIFIC_FREE_TIER_ACCESS_AND_CAPACITY_RECEIPT","BRAIN_EVALUATION_ADAPTER","BRAIN_SCORE"]
assert routes["deduplication"]["root2_only_predicate_count"]==15
assert routes["deduplication"]["unique_benchmark_surface_count"]==14

assert vec["authority"]["route_inventory_git_blob_sha"]=="9f93503d6ee0ac95c63fc7a4dafc1f75f2e48294"
assert len(vec["surfaces"])==14
assert sum(len(x["predicates"]) for x in vec["surfaces"])==15
assert vec["semantic_delta"]["comparator_targets_changed"] is False
assert rb["current_inputs"]["route_inventory_git_blob_sha"]=="9f93503d6ee0ac95c63fc7a4dafc1f75f2e48294"
assert rb["current_inputs"]["comparator_vector_git_blob_sha"]=="b28af5176550aba9e44ffd8ac9fde4fa7ba388bf"
assert rb["invariants"]["total_root2_involved_predicates"]==19
assert rb["fresh_reality_authority"] is False

e=cut["exact_state"]
assert (e["accepted_families"],e["proved_atomic"],e["unresolved_atomic"])==(5,12,26)
assert (e["root2_only_count"],e["root3_only_count"],e["root2_and_root3_count"])==(16,7,3)
assert cut["authority"]["root2_routes"]["git_blob_sha"]=="9f93503d6ee0ac95c63fc7a4dafc1f75f2e48294"
assert cut["authority"]["chartography_zero_spend_guard"]["status"].startswith("ACTIVE__INDEPENDENT")
assert cut["incremental_spend_usd"]==0 and cut["terminal_cases_consumed"]==0 and cut["fresh_reality_authority"] is False

assert front["authority"]["root2_fixed_bar_route_inventory"]["git_blob_sha"]=="9f93503d6ee0ac95c63fc7a4dafc1f75f2e48294"
assert front["root2_fixed_bar_hypergraph_rebind"]["status"]=="PENDING_INDEPENDENT_VERIFICATION"
assert front["fresh_reality_authority"] is False
assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False
assert "CHARTOGRAPHY_ZERO_SPEND_GUARD_DISCHARGED" in term["next_terminal_action"]
assert "FIXED_BAR_HYPERGRAPH_REBIND_V4_PENDING_VERIFICATION" in term["next_terminal_action"]
print(json.dumps({"status":"PASS__CHARTOGRAPHY_ZERO_SPEND_GUARD_DISCHARGED__ROOT2_FIXED_BAR_ROUTE_REBOUND__16_R2_ONLY__3_MIXED__ZERO_CREDIT","root2_involved":19,"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,"terminal_cases_consumed":0,"incremental_spend_usd":0,"fresh_reality_authority":False},sort_keys=True))
