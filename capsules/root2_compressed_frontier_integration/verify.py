#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

CAND={
 "canonical/action_intents/2026-10-04_ROOT2_ROUTE_COMPRESSION_V2_INTEGRATION_V1.json":"636fc435228c59d568c4be8a532dff25142ebb15",
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"2bc49e7335c0aa04149bbdb7b9a4cbee4031e6ff",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"a2001e4bb1db9eb3e394740a084357ece484d243",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"0591c9d281744b6c6119fb0eb1a08ffbbe0031fd",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"3634ad30a53d65f5ceee123a8724d85cabf35d8b",
}
BASE={
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"9bf96b66aadd2fcc075eccfacfd3b179684e9b41",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"5fe71dcc8a44274f2608e07a2a6c1b8dd12bd0f3",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"51115a11f4a89b78a094cde4637f82b5079493fd",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"0547c48a7bfce668131013fc887838cb5990e4dc",
}
SUPPORT={
 "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"46decd553126fadd5b54313ed976cdff7ca6bf42",
 "canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json":"10a28a403dae6df94f8fe58b1d9d3f9e0b60c11b",
 "canonical/verification/ROOT3_MINIMUM_ACTION_CUT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"e24058eab431a1643dae340a8ff564490f992097",
 "canonical/verification/HLE_OPUS55_ROUTE_TRUTH_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"2d4c75810e7de516019b4cd6553514c52fb9af09",
 "canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"de0c8c3045798e273e7aaba84162a920f89a43ad",
 "canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"288f0924157b0c0af0ff6bf302a56944f69f2fba",
 "canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"4290221e46c05af4c4cb4bc479c800564d9a41c2",
}

def blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def check(group, sub):
    for rel,exp in group.items():
        got=blob(ROOT/sub/rel)
        assert got==exp,(sub,rel,got,exp)
def load(sub,rel):
    return json.loads((ROOT/sub/rel).read_text())

check(CAND,"candidate")
check(BASE,"base")
check(SUPPORT,"support")

intent=load("candidate","canonical/action_intents/2026-10-04_ROOT2_ROUTE_COMPRESSION_V2_INTEGRATION_V1.json")
inv=load("candidate","canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
cut=load("candidate","canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
front=load("candidate","canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
auth=load("candidate","canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

binv=load("base","canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
bcut=load("base","canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
bfront=load("base","canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
bauth=load("base","canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

root=load("support","canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
r3=load("support","canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json")
r3v=load("support","canonical/verification/ROOT3_MINIMUM_ACTION_CUT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
hlev=load("support","canonical/verification/HLE_OPUS55_ROUTE_TRUTH_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osboot=load("support","canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
compv=load("support","canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osv=load("support","canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

# Current-base action intent.
assert intent["base_commit_sha"]=="60c6862de6283981e043a9c118aa213c9a66f464"
assert intent["concurrent_base_reconciliation"]["changed_authority_paths_overlap"] is False
assert intent["concurrent_base_reconciliation"]["mergeability"]=="TRUE"
for k in ["incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed",
          "acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert intent[k]==0,(k,intent[k])
for k in ["execution_authority","promotion_authority","fresh_reality_authority"]:
    assert intent[k] is False,(k,intent[k])

# Truth counts and root partition must not move.
assert auth["truth"]==bauth["truth"]
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["achieved"] is False
assert auth["atomic_acceptance_frontier"]["proved"]==12
assert auth["atomic_acceptance_frontier"]["unresolved"]==26
assert auth["ownership_state"]["verified_owned_families"]==5
assert auth["ownership_state"]["acceptance_open_families"]==14
assert auth["ownership_state"]["terminal_goal_achieved"] is False
assert cut["exact_state"]==bcut["exact_state"]
assert front["exact_state"]==bfront["exact_state"]
assert inv["deduplication"]==binv["deduplication"]

# Root1 and Root3 truth preserved.
r1=root["roots"]["root_1_capability_missing"]
assert r1["current_positive_root1_blockers"]==[]
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
r3state=root["root3_current_execution_state"]
assert r3state["currently_runnable_event_count"]==0
assert r3state["status"].startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS")
assert r3["currently_runnable_event_count"]==0
assert r3v["independent_runner"]["conclusion"]=="success"

# Supporting Root2 receipts independently passed.
assert compv["independent_runner"]["conclusion"]=="success"
assert compv["verified"]["automationbench_public_private_nonsubstitution"] is True
assert compv["verified"]["chartography_minimum_judge_calls"]==1000
assert compv["verified"]["gemini_limits_per_project"] is True
assert compv["verified"]["gemini_actual_capacity_not_guaranteed"] is True
assert osv["independent_runner"]["conclusion"]=="success"
assert osv["verified"]["gitlab_release_revision_absent"] is True

routes={x["surface"]:x for x in inv["routes"]}

# AutomationBench: no repeat of disproven public/private substitution route.
auto=routes["AutomationBench"]
assert "SATURATED" in auto["state"]
assert auto["route_compression_v2"]["search_state"]=="SATURATED_CURRENT_BOUND_EVIDENCE"
assert "PROVE_PUBLIC_600_ABSOLUTE_ROUTE_SCOPE_SUFFICIENT" not in auto["next"]
assert any(x["class"]=="AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH" for x in inv["exhausted_or_waiting"])
assert not any(x["surface"]=="AutomationBench public 600" for x in cut["active_zero_reality_work"])
assert any(x["class"]=="AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH" for x in cut["exhausted_or_waiting"])

# Chartography: exact call mass, no invented account quota.
chart=routes["Chartography with tools"]
assert chart["route_compression_v2"]["exact_minimum_judge_calls"]==1000
assert chart["route_compression_v2"]["generic_public_search"]=="SATURATED"
assert chart["route_compression_v2"]["residual"]=="PROJECT_SPECIFIC_ACCOUNT_CAPACITY"
chart_work=next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="Chartography with tools")
assert "1000_JUDGE_CALLS" in chart_work
assert "PROJECT_SPECIFIC" in chart_work
assert any(x["class"]=="CHARTOGRAPHY_GENERIC_PRICE_AND_QUOTA_SEARCH" for x in cut["exhausted_or_waiting"])

# HLE correction survives: Opus 4.6 grader, not stale o3-mini.
hle=routes["Humanity's Last Exam with tools"]
assert hle["opus55_route_truth"]["vendor_grader"]=="Claude Opus 4.6"
assert hle["opus55_route_truth"]["stale_default_judge_interpretation"]=="DELETED_FOR_FROZEN_OPUS55_COMPARATOR"
assert "OPUS_4_6" in next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="HLE with tools")
assert "Claude Opus 4.6" in json.dumps(hlev)

# OSWorld boot pass survives and source discovery only shrinks.
osw=routes["OSWorld 2.1 partial"]
assert "ZERO_COST_KVM_AND_PINNED_VM_BOOT_INDEPENDENT_PASS" in osw["state"]
assert osw["zero_case_boot"]["removed"]==["ZERO_COST_KVM_CARRIER","PINNED_VM_BOOT"]
assert osw["source_boundary_v1"]["gitlab_release_revision_pinned"] is False
assert "ZERO_COST_KVM_CARRIER" not in osw["next"]
assert "PINNED_VM_BOOT" not in osw["next"]
os_work=next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="OSWorld 2.1 partial")
assert "KVM" not in os_work and "VM_BOOT" not in os_work
assert "HUGGINGFACE" in os_work and "GITLAB" in os_work
assert osboot["independent_runner"]["conclusion"]=="success" or "PASS" in osboot["status"]

# Candidate authority pointers are exact.
assert auth["sources"]["root2_fixed_bar_route_inventory_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"]
assert auth["sources"]["root2_root3_minimum_execution_frontier_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]
assert auth["sources"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]==CAND["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"]
assert auth["sources"]["root2_route_compression_v2"]["verification_git_blob_sha"]==SUPPORT["canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert auth["sources"]["osworld_v21_self_host_source_boundary"]["verification_git_blob_sha"]==SUPPORT["canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]

# No execution/fresh reality sneaked in.
for obj in (cut,front):
    assert obj["execution_authority"] is False
    assert obj["fresh_reality_authority"] is False
assert "ROOT2_ONLY_LIVE_ZERO_REALITY_FRONTIER" in auth["next_terminal_action"]
assert "NO_AUTOMATIONBENCH_PUBLIC600_REPEAT" in auth["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_COMPRESSED_FRONTIER_INTEGRATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__CURRENT_BASE__TRUTH_COUNTS_PRESERVED__AUTOMATIONBENCH_SEARCH_DELETED__CHARTOGRAPHY_1000_CALL_ACCOUNT_RESIDUAL__HLE_CORRECTION_PRESERVED__OSWORLD_BOOT_AND_SOURCE_COMPRESSION_PRESERVED__ROOT1_ZERO__ROOT3_ZERO_RUNNABLE__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
