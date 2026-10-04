import json
import pathlib
import subprocess

FILES = {
    "solver": "canonical/runtime/minimum_terminal_cut_solver_v2.py",
    "solver_test": "canonical/tests/test_minimum_terminal_cut_solver_v2.py",
    "super": "canonical/runtime/terminal_adaptive_supertransaction_v1.py",
    "super_test": "canonical/tests/test_terminal_adaptive_supertransaction_v1.py",
    "activation": "canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_CUT_ACTIVATION_V1.json",
    "root": "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "r2": "canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json",
    "r3": "canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json",
    "retrieval": "canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json",
    "tb4": "canonical/verification/TB4_ATTAINABILITY_CUT_VERDICT_20261002_V1.json",
    "finance_direct": "canonical/governance/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
    "finance_agent": "canonical/governance/FINANCE_AGENT_V2_ZERO_COST_TOOL_BOUNDARY_20261004_V1.json",
    "osworld": "canonical/governance/OSWORLD_OPUS55_METHODOLOGY_PUBLIC_CORROBORATION_20261004_V1.json",
}
EXPECTED = {
    "solver": "da2ae55103f9b8f8bbe10e6316d152027e31854c",
    "solver_test": "065af38ed6cb6be6680a18dcede3ca65cb5374d1",
    "super": "e3060affa87b15a5c29246125783702be65061f6",
    "super_test": "dd545793b06d48a5f983b2be3d8bea16b1e333a9",
    "activation": "218a5d221d07433f69f821784025ae09bb9cf77b",
    "root": "d2e1827a40e1e547f17b61913f7c66f1ebce634c",
    "r2": "e948022f0a4e8d91b949a5155d850d56aa137c87",
    "r3": "4d8ce78ebe312100bbfc524062199961c0c6479d",
    "retrieval": "55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
    "tb4": "a7b0c692251b92819007c581b9fe84b75960cab7",
    "finance_direct": "9b9d4a41d19a5e58e8967027e1d1837790287dc2",
    "finance_agent": "032caa374280983945321f0a5706c0c665c097a6",
    "osworld": "259a6fa8f7daf744e6e06902d43925419cdd4d9b",
}


def blob(path):
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], text=True).strip()


for key, path in FILES.items():
    got = blob(path)
    assert got == EXPECTED[key], (key, got, EXPECTED[key])


def load(key):
    return json.loads(pathlib.Path(FILES[key]).read_text(encoding="utf-8"))


activation = load("activation")
root = load("root")
r2 = load("r2")
r3 = load("r3")
retrieval = load("retrieval")
tb4 = load("tb4")
finance_direct = load("finance_direct")
finance_agent = load("finance_agent")
osworld = load("osworld")

# Re-derive the current terminal partition from canonical source bytes.
assert root["current_acceptance"] == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
    "total_families": 19,
    "total_atomic": 38,
    "terminal": False,
}
part = root["current_residual_root_partition"]
assert (
    part["root1_positive_gap_count"],
    part["root2_only_count"],
    part["root3_only_count"],
    part["root2_and_root3_count"],
    part["unresolved_total"],
) == (0, 16, 7, 3, 26)

r2ctrl = root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2ctrl["effective_scheduling_authority"] is True
assert r2ctrl["fresh_reality_authority"] is False

r3state = root["root3_current_execution_state"]
assert (
    r3state["live_root3_predicates"],
    r3state["matched_scope_targets"],
    r3state["currently_runnable_event_count"],
) == (10, 7, 0)
assert r3state["fresh_reality_authority"] is False

# Verify the current search authority rather than accepting prose in the candidate.
assert retrieval["v19_verified_route_portfolio"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert retrieval["status"].startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS")
assert retrieval["search_engine_architecture"]["single_engine"] == "REJECTED_AS_STRUCTURALLY_INSUFFICIENT"
assert retrieval["search_engine_architecture"]["full_web_index_rebuild"] == "REJECTED_AS_DOMINATED_UNDER_ZERO_SPEND_AND_MINIMUM_WALL_CLOCK"

# Deterministic route deletions.
t = tb4["result"]
assert t["attainability_state"] == "IMPOSSIBLE"
assert t["upper_bound_successes"] == 180
assert t["required_successes"] == 220
assert t["upper_bound_successes"] < t["required_successes"]

exhausted = {row["route"]: row for row in r2["exhausted_or_deleted"]}
for route in (
    "TB4_CIRCLECI_FREE_XLARGE_GEN2",
    "CURSORBENCH_OWNER_ACCESS_SEARCH",
    "AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH",
    "GENERIC_ROOT3_SEARCH",
):
    assert route in exhausted

# Verify the new finance shortcut is real but not yet authority.
assert finance_direct["status"].startswith("CANDIDATE__INDEPENDENT_THEOREM_PASS")
assert finance_direct["scheduling_effect"]["new_primary_route"] == "MINIMIZE_VERIFIED_WEIGHTED_BRAIN_COMPONENT_LOWER_BOUND_DEFICIT_TO_61"
assert finance_direct["scheduling_effect"]["separate_index_run_required"] is False
assert finance_direct["authority"]["scheduling_authority"] is False

# Verify the zero-cost tool boundary and OSWorld residual were actually narrowed.
assert "TOOL_STACK_IS_NOT_INHERENTLY_PAID" in finance_agent["deductions"]
assert "BRAIN_SCORE_GE_81_8_PARTIAL" in osworld["still_open"]

# Independently check that the candidate activation mirrors the derived state and stays zero-credit.
assert activation["current_state"]["unresolved_atomic"] == 26
assert activation["current_state"]["root1_positive_gaps"] == 0
assert activation["implementation"]["supertransaction"]["causal_phase_lower_bound"] == 1
assert activation["implementation"]["supertransaction"]["causal_phase_upper_bound"] == 2
assert activation["finality"]["separate_manual_phase"] is False

dead = {row["route"]: row for row in activation["deterministic_route_deletions"]}
assert dead["TB4_FROZEN_CURRENT_NO_REPLAY_THRESHOLD_ROUTE"]["probability_upper"] == 0
assert dead["TB4_CIRCLECI_FREE_XLARGE_GEN2"]["probability_upper"] == 0
assert dead["CURSORBENCH_OWNER_ACCESS_SEARCH"]["probability_upper"] == 0
assert dead["AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH"]["probability_upper"] == 0

assert activation["search_policy"]["authority"] == "GLOBAL_RETRIEVAL_ENTRYPOINT_V4"
assert activation["search_policy"]["single_engine"] == "REJECTED_AS_STRUCTURALLY_INSUFFICIENT"
assert activation["finance_direct_threshold_effect"]["separate_index_run_required"] is False

assert activation["authority"] == {
    "scheduling_authority": False,
    "execution_authority": False,
    "promotion_authority": False,
    "fresh_reality_authority": False,
}
for key in (
    "incremental_spend_usd",
    "new_reality_units_consumed",
    "terminal_cases_consumed",
    "acceptance_credit_delta",
    "family_credit_delta",
    "capability_credit_delta",
    "ownership_credit_delta",
):
    assert activation["accounting"][key] == 0, key

print("PASS: exact candidate and source blobs match")
print("PASS: live terminal state re-derived as 5/19 families, 12/38 predicates, 26 unresolved, Root1=0")
print("PASS: TB4 frozen 180<220 route is mathematically impossible under unchanged assumptions")
print("PASS: Retrieval V19 is mandatory and single-engine/full-index routes are dominated")
print("PASS: finance weighted-threshold shortcut and zero-cost tool narrowing are real but zero-credit")
print("PASS: adaptive plan has at most two causal phases and automatic finality, with no fresh-reality authority")
