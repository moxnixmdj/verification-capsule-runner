import json
from pathlib import Path

def load(name):
    return json.loads(Path("verification_inputs", name).read_text())

def zero_accounting(o):
    a=o["accounting"]
    assert a["incremental_spend_usd"] == 0
    assert a["new_reality_units_consumed"] == 0
    assert a["terminal_cases_consumed"] == 0
    assert a["acceptance_credit_delta"] == 0
    assert a["family_credit_delta"] == 0
    assert a["capability_credit_delta"] == 0
    assert a["ownership_credit_delta"] == 0

terminal=load("root2_v10_terminal_active.json")
bridge=load("root2_v10_bridge_active.json")
root=load("root2_v10_root_state_active.json")
activation=load("root2_v10_final_activation.json")
frontier=load("root2_v10_frontier.json")
composition=load("root2_v10_composition_receipt.json")
projection=load("root2_v10_pointer_projection_receipt.json")
routing_activation=load("root2_v10_routing_activation.json")
routing=load("root2_v10_routing_receipt.json")
deletions=load("root2_primary_source_deletions_receipt.json")

FRONTIER_PATH="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
FRONTIER_SHA="2012926814d0d06405da56da64e589b06fef1756"
COMP_PATH="canonical/verification/ROOT2_V10_COMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
COMP_SHA="226832c5e9d5f4121f26d93bd645ed51dce474fe"
ACT_PATH="canonical/governance/ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1.json"
ACT_SHA="f5eda02fcc104bc8a5e13a82bfc8ec3d9515dcb2"
ROUTING_ACT_PATH="canonical/governance/ROOT2_EXTERNAL_FACT_ACQUISITION_OVERLAY_V2_ACTIVATION_V1.json"
ROUTING_ACT_SHA="400cf1fa6516d384b8781201841c3359851b070b"
ROUTING_REC_PATH="canonical/verification/ROOT2_V10_ACTIVATION_ROUTING_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
ROUTING_REC_SHA="5e5bf1082a8d7ce5b1fcd2c7b16a4d9d8acdc76d"

# Immutable prerequisite receipts.
assert frontier["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10"
assert composition["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert composition["independent_runner"]["workflow_run_id"]==37173112437
assert composition["independent_runner"]["workflow_job_id"]==111349972260
assert composition["independent_runner"]["conclusion"]=="success"
assert projection["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert projection["independent_runner"]["workflow_run_id"]==37173464316
assert projection["independent_runner"]["workflow_job_id"]==111351076362
assert projection["independent_runner"]["conclusion"]=="success"
assert projection["verified"]["effective_scheduling_authority"] is False
assert routing["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert routing["independent_runner"]["conclusion"]=="success"
assert routing_activation["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert routing_activation["authority"]=={
    "scheduling": True,
    "effective_scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
assert deletions["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert len(deletions["verified"]) >= 1
assert deletions["accounting"]["acceptance_credit_delta"]==0
assert deletions["fresh_reality_authority"] is False

# Final activation is scheduling-only, not terminal credit.
assert activation["schema"]=="PROJECT_BRAIN_ROOT2_FRONTIER_V10_FINAL_ACTIVATION_V1"
assert activation["status"].startswith("ACTIVE__V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS")
assert activation["frontier"]=={"path":FRONTIER_PATH,"git_blob_sha":FRONTIER_SHA}
assert activation["composition_verification"]["path"]==COMP_PATH
assert activation["composition_verification"]["git_blob_sha"]==COMP_SHA
assert activation["composition_verification"]["conclusion"]=="success"
assert activation["authority"]=={
    "scheduling": True,
    "effective_scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
zero_accounting(activation)

# Terminal authority, root state, and measurement bridge must agree exactly.
t=terminal["sources"]["root2_closure_v2_current_frontier"]
assert t["path"]==FRONTIER_PATH and t["git_blob_sha"]==FRONTIER_SHA
assert t["verification"]==COMP_PATH and t["verification_git_blob_sha"]==COMP_SHA
assert t["activation"]==ACT_PATH and t["activation_git_blob_sha"]==ACT_SHA
assert t["effective_scheduling_authority"] is True
assert t["status"].startswith("ACTIVE__ROOT2_FRONTIER_V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS")
assert terminal["ownership_state"]["verified_owned_families"]==5
assert terminal["ownership_state"]["acceptance_open_families"]==14
assert terminal["ownership_state"]["terminal_goal_achieved"] is False
assert "ACTIVE_ROOT2_V10" in terminal["next_terminal_action"]

r=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r["current_frontier_path"]==FRONTIER_PATH and r["current_frontier_git_blob_sha"]==FRONTIER_SHA
assert r["current_frontier_verification_path"]==COMP_PATH and r["current_frontier_verification_git_blob_sha"]==COMP_SHA
assert r["current_frontier_activation_path"]==ACT_PATH and r["current_frontier_activation_git_blob_sha"]==ACT_SHA
assert r["effective_scheduling_authority"] is True
assert r["fresh_reality_authority"] is False
assert r["external_fact_acquisition_overlay"]["activation_path"]==ROUTING_ACT_PATH
assert r["external_fact_acquisition_overlay"]["activation_git_blob_sha"]==ROUTING_ACT_SHA
assert r["external_fact_acquisition_overlay"]["verification_path"]==ROUTING_REC_PATH
assert r["external_fact_acquisition_overlay"]["verification_git_blob_sha"]==ROUTING_REC_SHA
assert r["external_fact_acquisition_overlay"]["self_service_fact_count"]==9
assert r["external_fact_acquisition_overlay"]["owner_exclusive_fact_count"]==6
assert r["external_fact_acquisition_overlay"]["owner_or_direct_platform_receipt_count"]==1
assert r["external_fact_acquisition_overlay"]["dormant_fact_count"]==2
assert r["external_fact_acquisition_overlay"]["low_value_support_waits"]==0
assert root["scheduler_policy"]["root2_current_frontier"]==FRONTIER_PATH
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["open_families"]==14
assert root["current_acceptance"]["proved_atomic"]==12
assert root["current_acceptance"]["unresolved_atomic"]==26
assert root["current_acceptance"]["terminal"] is False

b=bridge["root2_closure_controller_v2"]
assert b["frontier_path"]==FRONTIER_PATH and b["frontier_git_blob_sha"]==FRONTIER_SHA
assert b["frontier_verification_path"]==COMP_PATH and b["frontier_verification_git_blob_sha"]==COMP_SHA
assert b["frontier_activation_path"]==ACT_PATH and b["frontier_activation_git_blob_sha"]==ACT_SHA
assert b["effective_scheduling_authority"] is True
assert b["status"].startswith("ACTIVE__ROOT2_FRONTIER_V10_COMPOSITION_PASS__POINTER_PROJECTION_PASS__V10_ACQUISITION_ROUTING_PASS")
assert "CURRENT_ROOT2_V10" in bridge["next"]
assert bridge["incremental_spend_usd"]==0
assert bridge["terminal_cases_consumed"]==0
assert bridge["acceptance_credit_delta"]==0
assert bridge["fresh_reality_authority"] is False

# Cross-surface invariants.
assert frontier["exact_state"]["accepted_families"]==5
assert frontier["exact_state"]["open_families"]==14
assert frontier["exact_state"]["proved_atomic"]==12
assert frontier["exact_state"]["unresolved_atomic"]==26
assert frontier["exact_state"]["root1_positive_gap_count"]==0
assert frontier["accounting"]["incremental_spend_usd"]==0
assert frontier["accounting"]["terminal_cases_consumed"]==0
assert frontier["accounting"]["acceptance_credit_delta"]==0
assert frontier["fresh_reality_authority"] is False

print("ROOT2_V10_TERMINAL_BRIDGE_COHERENCE: PASS")
