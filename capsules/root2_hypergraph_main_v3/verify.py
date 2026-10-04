import json
from pathlib import Path

R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())

route=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
vec=load("ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json")
reb=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V3.json")

ROUTE_SHA="71495ebcf456119f4df694203631aeeb3048c81a"
VECTOR_SHA="f426f1aa136abdcc33a14716fe4edbc40003bf2a"

assert vec["authority"]["route_inventory_git_blob_sha"]==ROUTE_SHA
assert vec["semantic_delta"]["current_route_inventory_git_blob_sha"]==ROUTE_SHA
assert vec["semantic_delta"]["route_state_only"] is True
assert vec["semantic_delta"]["comparator_targets_changed"] is False
assert vec["semantic_delta"]["predicate_set_changed"] is False
assert vec["semantic_delta"]["surface_set_changed"] is False

rmap={x["surface"]:x for x in route["routes"]}
vmap={x["surface"]:x for x in vec["surfaces"]}
assert route["deduplication"]["root2_only_predicate_count"]==15
assert route["deduplication"]["unique_benchmark_surface_count"]==14
assert len(vmap)==14
assert sum(len(x["predicates"]) for x in vec["surfaces"])==15
assert set(rmap)==set(vmap)
for name,row in vmap.items():
    assert row["predicates"]==rmap[name]["predicate_ids"], name
    assert row["target"]==rmap[name]["target"], name

assert "PUBLIC600_SEARCH_SATURATED" in vmap["AutomationBench"]["route_class"]
assert "ADAPTER_DISCHARGED" in vmap["Humanity's Last Exam with tools"]["route_class"]
assert vmap["Chartography with tools"]["route_class"]=="PROJECT_ACCOUNT_CAPACITY_THEN_SCORE"
osw=vmap["OSWorld 2.1 partial"]["route_class"]
assert "FUNCTIONAL_PROTOCOL" in osw
assert "EXACT_GITLAB_REVISION_BLOCKERS_DISCHARGED" in osw

assert reb["current_inputs"]["route_inventory_git_blob_sha"]==ROUTE_SHA
assert reb["current_inputs"]["comparator_vector_git_blob_sha"]==VECTOR_SHA
assert reb["invariants"]["fixed_bar_predicates"]==15
assert reb["invariants"]["unique_fixed_bar_surfaces"]==14
assert reb["invariants"]["total_root2_involved_predicates_after_synthesis_reclassification"]==19
assert reb["invariants"]["comparator_targets_changed"] is False
assert reb["invariants"]["predicate_set_changed"] is False
assert reb["invariants"]["surface_set_changed"] is False
assert "SYNTHESIS_ROOT2_ONLY_RESIDUAL_IS_NOT_A_FIXED_BAR_SURFACE_AND_IS_SCHEDULED_SEPARATELY" in reb["hard_rules"]
assert reb["fresh_reality_authority"] is False
assert reb["terminal_cases_consumed"]==0
assert reb["incremental_spend_usd"]==0
assert reb["acceptance_credit_delta"]==0

print(json.dumps({
 "status":"PASS__MAIN_ROOT2_HYPERGRAPH_V3_EXACT_INPUT_REBIND__15_FIXED_BAR_PREDICATES__14_SURFACES__19_TOTAL_ROOT2_INVOLVED__TARGETS_UNCHANGED__ZERO_CREDIT",
 "route_blob":ROUTE_SHA,
 "vector_blob":VECTOR_SHA,
 "rebind_blob":"244f4fcdc07ee149fc4370dc52f4de90cbd87db9"
},sort_keys=True))
