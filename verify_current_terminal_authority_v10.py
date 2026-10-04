import json
from pathlib import Path

def load(name):
    return json.loads(Path("verification_inputs", name).read_text())

terminal=load("current_terminal_v10.json")
root=load("current_root_v10.json")
bridge=load("current_bridge_v10.json")
activation=load("v10_final_activation.json")
frontier=load("v10_frontier.json")
composition=load("v10_composition_receipt.json")
routing=load("v10_routing_receipt.json")
deletions=load("primary_source_deletions_receipt.json")
terminal_receipt=load("v10_final_terminal_receipt.json")

FRONTIER="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
FRONTIER_SHA="2012926814d0d06405da56da64e589b06fef1756"
COMP="canonical/verification/ROOT2_V10_COMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
COMP_SHA="226832c5e9d5f4121f26d93bd645ed51dce474fe"
ACT="canonical/governance/ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1.json"
ACT_SHA="f5eda02fcc104bc8a5e13a82bfc8ec3d9515dcb2"

def assert_zero(a):
    assert a["incremental_spend_usd"] == 0
    if "new_reality_units_consumed" in a:
        assert a["new_reality_units_consumed"] == 0
    assert a["terminal_cases_consumed"] == 0
    assert a["acceptance_credit_delta"] == 0
    if "family_credit_delta" in a:
        assert a["family_credit_delta"] == 0
    if "capability_credit_delta" in a:
        assert a["capability_credit_delta"] == 0
    if "ownership_credit_delta" in a:
        assert a["ownership_credit_delta"] == 0

# Immutable V10 proof chain.
assert frontier["schema"] == "PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10"
assert frontier["exact_state"]["accepted_families"] == 5
assert frontier["exact_state"]["open_families"] == 14
assert frontier["exact_state"]["proved_atomic"] == 12
assert frontier["exact_state"]["unresolved_atomic"] == 26
assert frontier["exact_state"]["root1_positive_gap_count"] == 0
assert frontier["execution_authority"] is False
assert frontier["promotion_authority"] is False
assert frontier["fresh_reality_authority"] is False
assert_zero(frontier["accounting"])

assert composition["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert composition["independent_runner"]["conclusion"] == "success"
assert composition["verified"]["exact_state_unchanged"] is True
assert composition["verified"]["execution_authority"] is False
assert composition["verified"]["promotion_authority"] is False
assert composition["verified"]["fresh_reality_authority"] is False
assert_zero(composition["accounting"])

assert activation["schema"] == "PROJECT_BRAIN_ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1"
assert activation["status"].startswith("ACTIVE__V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS")
assert activation["frontier"] == {"path": FRONTIER, "git_blob_sha": FRONTIER_SHA}
assert activation["composition_verification"]["path"] == COMP
assert activation["composition_verification"]["git_blob_sha"] == COMP_SHA
assert activation["composition_verification"]["conclusion"] == "success"
assert activation["authority"] == {
    "scheduling": True,
    "effective_scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
assert_zero(activation["accounting"])

# Existing independent active-state receipts.
assert routing["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert routing["independent_runner"]["conclusion"] == "success"
assert routing["accounting"]["acceptance_credit_delta"] == 0
assert routing["fresh_reality_authority"] is False

assert deletions["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert deletions["accounting"]["acceptance_credit_delta"] == 0
assert deletions["fresh_reality_authority"] is False

assert terminal_receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert terminal_receipt["independent_runner"]["conclusion"] == "success"
assert terminal_receipt["accounting"]["acceptance_credit_delta"] == 0
assert terminal_receipt["fresh_reality_authority"] is False

# CURRENT_TERMINAL_AUTHORITY must now agree with already-active root + bridge.
t=terminal["sources"]["root2_closure_v2_current_frontier"]
assert t["path"] == FRONTIER
assert t["git_blob_sha"] == FRONTIER_SHA
assert t["verification"] == COMP
assert t["verification_git_blob_sha"] == COMP_SHA
assert t["activation"] == ACT
assert t["activation_git_blob_sha"] == ACT_SHA
assert t["effective_scheduling_authority"] is True
assert t["status"].startswith("ACTIVE__ROOT2_FRONTIER_V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS")
assert "ACTIVE_ROOT2_V10" in terminal["next_terminal_action"]
assert terminal["ownership_state"]["verified_owned_families"] == 5
assert terminal["ownership_state"]["acceptance_open_families"] == 14
assert terminal["ownership_state"]["terminal_goal_achieved"] is False

r=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r["current_frontier_path"] == FRONTIER
assert r["current_frontier_git_blob_sha"] == FRONTIER_SHA
assert r["current_frontier_verification_path"] == COMP
assert r["current_frontier_verification_git_blob_sha"] == COMP_SHA
assert r["current_frontier_activation_path"] == ACT
assert r["current_frontier_activation_git_blob_sha"] == ACT_SHA
assert r["effective_scheduling_authority"] is True
assert r["fresh_reality_authority"] is False
assert r["external_fact_acquisition_overlay"]["self_service_fact_count"] == 9
assert r["external_fact_acquisition_overlay"]["owner_exclusive_fact_count"] == 6
assert r["external_fact_acquisition_overlay"]["owner_or_direct_platform_receipt_count"] == 1
assert r["external_fact_acquisition_overlay"]["dormant_fact_count"] == 2
assert r["external_fact_acquisition_overlay"]["low_value_support_waits"] == 0
assert r["primary_source_search_deletions"]["scheduler_deletion_count"] == 6
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["scheduler_policy"]["root2_current_frontier"] == FRONTIER
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert root["current_acceptance"]["accepted_families"] == 5
assert root["current_acceptance"]["open_families"] == 14
assert root["current_acceptance"]["proved_atomic"] == 12
assert root["current_acceptance"]["unresolved_atomic"] == 26
assert root["current_acceptance"]["terminal"] is False

b=bridge["root2_closure_controller_v2"]
assert b["frontier_path"] == FRONTIER
assert b["frontier_git_blob_sha"] == FRONTIER_SHA
assert b["frontier_verification_path"] == COMP
assert b["frontier_verification_git_blob_sha"] == COMP_SHA
assert b["frontier_activation_path"] == ACT
assert b["frontier_activation_git_blob_sha"] == ACT_SHA
assert b["effective_scheduling_authority"] is True
assert b["status"].startswith("ACTIVE__ROOT2_FRONTIER_V10_COMPOSITION_PASS__FINAL_ACTIVATION_BOUND")
assert "CURRENT_ROOT2_V10" in bridge["next"]
assert bridge["incremental_spend_usd"] == 0
assert bridge["terminal_cases_consumed"] == 0
assert bridge["acceptance_credit_delta"] == 0
assert bridge["fresh_reality_authority"] is False

# Cross-surface identity.
assert t["git_blob_sha"] == r["current_frontier_git_blob_sha"] == b["frontier_git_blob_sha"] == FRONTIER_SHA
assert t["activation_git_blob_sha"] == r["current_frontier_activation_git_blob_sha"] == b["frontier_activation_git_blob_sha"] == ACT_SHA
assert t["effective_scheduling_authority"] == r["effective_scheduling_authority"] == b["effective_scheduling_authority"] == True

print("CURRENT_TERMINAL_AUTHORITY_V10_COHERENCE: PASS")
