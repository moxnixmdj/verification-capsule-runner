import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())

v=load("ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json")
b=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V2.json")
r=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")

EXPECTED_ROUTE="71495ebcf456119f4df694203631aeeb3048c81a"
EXPECTED_VECTOR="350efbbce8e47b39fec52329e5b0770f9439fadd"

assert v["authority"]["route_inventory_git_blob_sha"]==EXPECTED_ROUTE
assert v["semantic_delta"]["current_route_inventory_git_blob_sha"]==EXPECTED_ROUTE
assert v["semantic_delta"]["comparator_targets_changed"] is False
assert v["semantic_delta"]["predicate_set_changed"] is False
assert v["semantic_delta"]["surface_set_changed"] is False
assert v["semantic_delta"]["route_state_only"] is True
assert len(v["surfaces"])==14
assert sum(len(x["predicates"]) for x in v["surfaces"])==15

assert r["deduplication"]["root2_only_predicate_count"]==15
assert r["deduplication"]["unique_benchmark_surface_count"]==14
rmap={x["surface"]:x for x in r["routes"]}
vmap={x["surface"]:x for x in v["surfaces"]}
assert set(rmap)==set(vmap)
for name,row in vmap.items():
    assert row["predicates"]==rmap[name]["predicate_ids"], name
    assert row["target"]==rmap[name]["target"], name

assert "SATURATED" in vmap["AutomationBench"]["route_class"]
assert "ADAPTER_DISCHARGED" in vmap["Humanity's Last Exam with tools"]["route_class"]
assert vmap["Chartography with tools"]["route_class"]=="PROJECT_ACCOUNT_CAPACITY_THEN_SCORE"
osw=vmap["OSWorld 2.1 partial"]["route_class"]
assert "FUNCTIONAL_PROTOCOL" in osw
assert "GITLAB_REVISION_DISCOVERY_DISCHARGED" in osw
assert "EXACT_REVISION" not in osw

assert b["current_inputs"]["route_inventory_git_blob_sha"]==EXPECTED_ROUTE
assert b["current_inputs"]["comparator_vector_git_blob_sha"]==EXPECTED_VECTOR
assert b["prior_independent_verification"]["runtime_git_blob_sha"]=="dd2094c4845239a0be4cfd34af4d8f3a7e411060"
assert b["prior_independent_verification"]["tests_git_blob_sha"]=="235db2f21fe4b0f70096be69ae28af87a5ce31dd"
assert b["prior_independent_verification"]["governance_git_blob_sha"]=="2793081a62a99cb69c9ae3e37323205e756cbebb"
assert b["invariants"]["root2_fixed_bar_predicates"]==15
assert b["invariants"]["unique_surfaces"]==14
assert b["invariants"]["comparator_targets_changed"] is False
assert b["invariants"]["predicate_set_changed"] is False
assert b["invariants"]["surface_set_changed"] is False
assert b["fresh_reality_authority"] is False
assert b["incremental_spend_usd"]==0
assert b["terminal_cases_consumed"]==0
assert b["acceptance_credit_delta"]==0

print(json.dumps({
 "status":"PASS__CURRENT_ROOT2_ROUTE_IDENTITY_REBOUND__15_FIXED_BAR_PREDICATES__14_SURFACES__TARGETS_UNCHANGED__OSWORLD_FALSE_REVISION_BLOCKER_DELETED__ZERO_CREDIT",
 "route_blob":EXPECTED_ROUTE,
 "vector_blob":EXPECTED_VECTOR
},sort_keys=True))
