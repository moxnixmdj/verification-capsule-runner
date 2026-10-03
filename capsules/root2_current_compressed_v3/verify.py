import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

route=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
cut=load("CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
front=load("ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
term=load("CURRENT_TERMINAL_AUTHORITY_V1.json")

assert route["deduplication"]["root2_only_predicate_count"]==15
assert route["deduplication"]["unique_benchmark_surface_count"]==14
rows={r["surface"]:r for r in route["routes"]}
assert "SATURATED" in rows["AutomationBench"]["state"]
assert rows["Chartography with tools"]["route_compression_v2"]["exact_minimum_judge_calls"]==1000
assert rows["OSWorld 2.1 partial"]["source_boundary_v1"]["gitlab_release_revision_pinned"] is False
assert rows["Humanity's Last Exam with tools"]["brain_tool_adapter"]["status"]=="ACTIVE__INDEPENDENTLY_VERIFIED"
assert rows["Humanity's Last Exam with tools"]["brain_tool_adapter"]["terminal_cases_consumed"]==0

s=cut["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["root1_positive_gap_count"]==0
assert cut["fresh_reality_authority"] is False
assert cut["execution_authority"] is False
assert all(x["surface"]!="AutomationBench public 600" for x in cut["active_zero_reality_work"])
assert any(x["class"]=="AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH" and "SATURATED" in x["state"] for x in cut["exhausted_or_waiting"])
assert any(x["class"]=="CHARTOGRAPHY_GENERIC_PRICE_AND_QUOTA_SEARCH" and "SATURATED" in x["state"] for x in cut["exhausted_or_waiting"])
assert cut["authority"]["root2_routes"]["git_blob_sha"]=="b273b4313d329e962ac749151d086e2b1e93c5ca"
assert cut["authority"]["hle_tool_adapter"]["verification_git_blob_sha"]=="942cd3032f8e1c53555f2df0810f82c86273f9ae"

fs=front["exact_state"]
assert fs["acceptance"]=="5/19_PASS__14/19_OPEN"
assert fs["proved_predicates"]==12 and fs["unresolved_predicates"]==26
assert fs["root1_positive_gap_count"]==0
assert front["authority"]["root2_fixed_bar_route_inventory"]["git_blob_sha"]=="b273b4313d329e962ac749151d086e2b1e93c5ca"
assert front["authority"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]=="8aba43f58cbf9b14aacc1aa259b2a63c32044fbb"
assert front["new_reality_units_consumed"]==0
assert front["incremental_spend_usd"]==0
assert front["fresh_reality_authority"] is False

assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False
assert term["sources"]["root2_fixed_bar_route_inventory_v1"]["git_blob_sha"]=="b273b4313d329e962ac749151d086e2b1e93c5ca"
assert term["sources"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]=="8aba43f58cbf9b14aacc1aa259b2a63c32044fbb"
assert term["sources"]["root2_root3_minimum_execution_frontier_v1"]["git_blob_sha"]=="4adb0e9642e26566e4e413e8a1951603b9013168"
assert "NO_AUTOMATIONBENCH_PUBLIC600_REPEAT" in term["next_terminal_action"]
assert "NO_HLE_ADAPTER_REPEAT" in term["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_CURRENT_COMPRESSED_V3_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_FOUR_AUTHORITY_BLOBS__ROUTE_DELETIONS_AND_HLE_ADAPTER_DISCHARGE__COUNTS_PRESERVED__ZERO_CASES__ZERO_SPEND",
 "accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,
 "terminal_cases_consumed":0,"incremental_spend_usd":0,
 "fresh_reality_authority":False,"promotion_authority":False
},sort_keys=True))
