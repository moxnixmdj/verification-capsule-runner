import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())
v=load("ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json")
b=load("ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V2.json")
r=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")

assert v["authority"]["route_inventory_git_blob_sha"]=="b273b4313d329e962ac749151d086e2b1e93c5ca"
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
    assert row["predicates"]==rmap[name]["predicate_ids"]
    assert row["target"]==rmap[name]["target"]

assert "ADAPTER_DISCHARGED" in vmap["Humanity's Last Exam with tools"]["route_class"]
assert "SATURATED" in vmap["AutomationBench"]["route_class"]
assert vmap["Chartography with tools"]["route_class"]=="PROJECT_ACCOUNT_CAPACITY_THEN_SCORE"
assert "SOURCE_DISCOVERY_DISCHARGED" in vmap["OSWorld 2.1 partial"]["route_class"]

assert b["current_inputs"]["route_inventory_git_blob_sha"]=="b273b4313d329e962ac749151d086e2b1e93c5ca"
assert b["current_inputs"]["comparator_vector_git_blob_sha"]=="853270f1f998ab6a3050d442fcaa4b9c512bb74c"
assert b["prior_independent_verification"]["runtime_git_blob_sha"]=="dd2094c4845239a0be4cfd34af4d8f3a7e411060"
assert b["prior_independent_verification"]["tests_git_blob_sha"]=="235db2f21fe4b0f70096be69ae28af87a5ce31dd"
assert b["prior_independent_verification"]["governance_git_blob_sha"]=="2793081a62a99cb69c9ae3e37323205e756cbebb"
assert b["invariants"]["root2_only_predicates"]==15
assert b["invariants"]["unique_surfaces"]==14
assert b["invariants"]["comparator_targets_changed"] is False
assert b["fresh_reality_authority"] is False
assert b["incremental_spend_usd"]==0
print(json.dumps({"status":"PASS__CURRENT_ROUTE_IDENTITY_REBOUND__15_PREDICATES_14_SURFACES__TARGETS_UNCHANGED__ZERO_CREDIT","route_blob":"b273b4313d329e962ac749151d086e2b1e93c5ca","vector_blob":"853270f1f998ab6a3050d442fcaa4b9c512bb74c"},sort_keys=True))
