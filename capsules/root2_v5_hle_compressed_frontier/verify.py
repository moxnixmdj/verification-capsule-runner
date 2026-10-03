#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

CAND={
 "canonical/action_intents/2026-10-04_ROOT2_V5_HLE_COMPRESSED_FRONTIER_INTEGRATION_V1.json":"dede76e2b5dcdc12c3339a82ca09e5a5c37d65a7",
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"bca14e3bc81dbf38e329020a789a0aaacdab36ed",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"34978940366f468256b9f9b780afb0feb78c3962",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"49b6df4ff8f1939014ac13229708f06cbbd65131",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"43177b70f688dac4b323cf979489f402d47e8695",
}
BASE={
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"16f82fed36c184b9630fedddebf9d8c52aa67d2d",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"c0486fd7430255e1376d7f1f179c1621861d89ec",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"b8dd84fbe2c7ba5cddf6d9fb6baad32a7ca91038",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"0ea52cd54cde7fd6f27b86254a3127d762964b5c",
}
SUPPORT={
 "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"afe7e055fbad7a04b169d2c0cac91b764ced20a8",
 "canonical/verification/HLE_OPUS55_POPULATION_ACCESS_CORRECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V2.json":"a62f0a2add46dc1fc5ee719592d929440e5522bb",
 "canonical/governance/HLE_OPUS55_TOOL_ADAPTER_ACTIVATION_V1.json":"95b5b520a8eb9b288e6818bf591a7ab9de379fd5",
 "canonical/verification/HLE_OPUS55_TOOL_ADAPTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"942cd3032f8e1c53555f2df0810f82c86273f9ae",
 "canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"de0c8c3045798e273e7aaba84162a920f89a43ad",
 "canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"288f0924157b0c0af0ff6bf302a56944f69f2fba",
 "canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"4290221e46c05af4c4cb4bc479c800564d9a41c2",
 "canonical/verification/UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"1001e25ca59c57b13049a22f305e487eb01f693a",
}
def blob(p:Path)->str:
 raw=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def check(group,sub):
 for rel,exp in group.items():
  got=blob(ROOT/sub/rel); assert got==exp,(sub,rel,got,exp)
def load(sub,rel): return json.loads((ROOT/sub/rel).read_text())
check(CAND,"candidate"); check(BASE,"base"); check(SUPPORT,"support")

intent=load("candidate","canonical/action_intents/2026-10-04_ROOT2_V5_HLE_COMPRESSED_FRONTIER_INTEGRATION_V1.json")
inv=load("candidate","canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
cut=load("candidate","canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
front=load("candidate","canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
auth=load("candidate","canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
binv=load("base","canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
bcut=load("base","canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
bfront=load("base","canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
bauth=load("base","canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
root=load("support","canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
hlev2=load("support","canonical/verification/HLE_OPUS55_POPULATION_ACCESS_CORRECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V2.json")
hleact=load("support","canonical/governance/HLE_OPUS55_TOOL_ADAPTER_ACTIVATION_V1.json")
hlevr=load("support","canonical/verification/HLE_OPUS55_TOOL_ADAPTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osboot=load("support","canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
compv=load("support","canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osv=load("support","canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v5vr=load("support","canonical/verification/UNIVERSAL_LEARNING_RECURSIVE_ABSTRACTION_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

assert intent["base_commit_sha"]=="570e6581a75a3b6af0b76f7b3c4efa695891e7e0"
assert intent["candidate_authority_blobs"]=={
 "root2_fixed_bar_route_inventory_v1":CAND["canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"],
 "current_zero_reality_minimum_cut_v8":CAND["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"],
 "root2_root3_minimum_execution_frontier_v1":CAND["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"],
 "current_terminal_authority_v1":CAND["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"],
}
for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert intent[k]==0,(k,intent[k])
for k in ("execution_authority","promotion_authority","fresh_reality_authority"): assert intent[k] is False

# No terminal truth movement.
assert auth["truth"]==bauth["truth"]
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["achieved"] is False
assert auth["atomic_acceptance_frontier"]==bauth["atomic_acceptance_frontier"]
assert auth["atomic_acceptance_frontier"]["proved"]==12 and auth["atomic_acceptance_frontier"]["unresolved"]==26
assert auth["ownership_state"]==bauth["ownership_state"]
assert inv["deduplication"]==binv["deduplication"]
assert cut["exact_state"]==bcut["exact_state"]
assert front["exact_state"]==bfront["exact_state"]

# Root1 / Root3 truth.
assert root["roots"]["root_1_capability_missing"]["current_positive_root1_blockers"]==[]
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
r3=root["root3_current_execution_state"]
assert r3["currently_runnable_event_count"]==0 and r3["fresh_reality_authority"] is False

# Preserve V5 and Root3 refinement exactly from base authority.
assert auth["sources"]["universal_learning_recursive_abstraction_v5"]==bauth["sources"]["universal_learning_recursive_abstraction_v5"]
assert front["authority"]["root3_residual_compression"]==bfront["authority"]["root3_residual_compression"]
assert cut["authority"]["root3_compression"]==bcut["authority"]["root3_compression"]
assert auth["sources"]["root3_scope_certificate_admissibility_refinement"]==bauth["sources"]["root3_scope_certificate_admissibility_refinement"]
assert front["authority"]["root3_scope_certificate_admissibility_refinement"]==bfront["authority"]["root3_scope_certificate_admissibility_refinement"]
assert v5vr["independent_runner"]["final_green"]["conclusion"]=="success"
assert v5vr["verified"]["unknown_domain_leaves_after"]==2
assert v5vr["verified"]["unknown_domain_leaves_closed"]==0
assert v5vr["verified"]["acceptance_truth_changed"] is False

# Supporting Root2 receipts.
assert compv["independent_runner"]["conclusion"]=="success"
assert compv["verified"]["automationbench_public_private_nonsubstitution"] is True
assert compv["verified"]["chartography_minimum_judge_calls"]==1000
assert osv["independent_runner"]["conclusion"]=="success"
assert osv["verified"]["gitlab_release_revision_absent"] is True
assert hlev2["protocol_verifier"]["conclusion"]=="success"
assert hlev2["access_verifier"]["conclusion"]=="success"
assert hlev2["verified"]["frozen_population_identity"]=="FULL_HLE_NOT_HLE_DIAMOND"
assert hlev2["verified"]["frozen_population_question_count"]==2500
assert hlev2["verified"]["grader"]=="Claude Opus 4.6"
assert osboot["runner"]["conclusion"]=="success"
assert osboot["verified"]["kvm"] is True

# HLE adapter: discharge exactly adapter, preserve one-sided soundness and residuals.
assert hleact["status"]=="ACTIVE__INDEPENDENTLY_VERIFIED__ZERO_CREDIT"
assert hleact["verification"]["conclusion"]=="success"
assert hleact["soundness"]["identical_vendor_backend_claim"] is False
assert hleact["remaining_hle_root2_residuals"]==[
 "MATERIAL_CAIS_HLE_FULL_2500_AUTO_GATE_ACCOUNT_ACCESS_WITHOUT_CONTAMINATION",
 "ZERO_COST_CLAUDE_OPUS_4_6_COMPARABLE_GRADER_OR_STRONGER_SCORER_RELATION",
 "BRAIN_SCORE_GE_67_7",
]
assert hlevr["independent_runner"]["conclusion"]=="success"
assert hlevr["verified"]["primary_pdf_policy_equality_153_of_153"] is True
assert hlevr["verified"]["one_sided_soundness_bound"] is True
assert hlevr["verified"]["identical_vendor_backend_claim"] is False

routes={r["surface"]:r for r in inv["routes"]}
auto=routes["AutomationBench"]
assert "SATURATED" in auto["state"]
assert auto["route_compression_v2"]["search_state"]=="SATURATED_CURRENT_BOUND_EVIDENCE"
assert not any(x["surface"]=="AutomationBench public 600" for x in cut.get("active_zero_reality_work",cut.get("active",[])))

chart=routes["Chartography with tools"]
assert chart["route_compression_v2"]["exact_minimum_judge_calls"]==1000
assert chart["route_compression_v2"]["residual"]=="PROJECT_SPECIFIC_ACCOUNT_CAPACITY"

hle=routes["Humanity's Last Exam with tools"]
assert hle["opus55_route_truth"]["population"]=="cais/hle"
assert hle["opus55_route_truth"]["population_question_count"]==2500
assert hle["opus55_route_truth"]["vendor_grader"]=="Claude Opus 4.6"
assert hle["opus55_tool_adapter_v1"]["discharged"]=="BRAIN_VENDOR_SEMANTICS_TOOL_ADAPTER"
assert hle["opus55_tool_adapter_v1"]["remaining"]==hleact["remaining_hle_root2_residuals"]
assert "ADAPTER" not in hle["next"] or "ACCOUNT_ACCESS" in hle["next"]

osw=routes["OSWorld 2.1 partial"]
assert "ZERO_COST_KVM_AND_PINNED_VM_BOOT_INDEPENDENT_PASS" in osw["state"]
assert osw["zero_case_boot"]["removed"]==["ZERO_COST_KVM_CARRIER","PINNED_VM_BOOT"]
assert osw["source_boundary_v1"]["gitlab_release_revision_pinned"] is False

# Scheduler exact reductions.
active=cut.get("active_zero_reality_work",cut.get("active",[]))
hlework=next(x["work"] for x in active if x["surface"]=="HLE with tools")
assert "TOOL_ADAPTER_ALREADY_DISCHARGED" in hlework
assert "CAIS_HLE_FULL_2500" in hlework
chartwork=next(x["work"] for x in active if x["surface"]=="Chartography with tools")
assert "1000_JUDGE_CALLS" in chartwork
oswork=next(x["work"] for x in active if x["surface"]=="OSWorld 2.1 partial")
assert "KVM" not in oswork and "VM_BOOT" not in oswork
assert "HUGGINGFACE" in oswork and "GITLAB" in oswork

# Top authority points to exact candidate bytes and verified adapter.
assert auth["sources"]["root2_fixed_bar_route_inventory_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"]
assert auth["sources"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]==CAND["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"]
assert auth["sources"]["root2_root3_minimum_execution_frontier_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]
assert auth["sources"]["hle_opus55_tool_adapter_v1"]["activation_git_blob_sha"]==SUPPORT["canonical/governance/HLE_OPUS55_TOOL_ADAPTER_ACTIVATION_V1.json"]
assert auth["sources"]["hle_opus55_tool_adapter_v1"]["verification_git_blob_sha"]==SUPPORT["canonical/verification/HLE_OPUS55_TOOL_ADAPTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]

for obj in (cut,front):
 assert obj["execution_authority"] is False
 assert obj["promotion_authority"] is False
 assert obj["fresh_reality_authority"] is False
assert "ROOT2_ONLY_LIVE_ZERO_REALITY_FRONTIER" in auth["next_terminal_action"]
assert "HLE_TOOL_ADAPTER_DISCHARGED" in auth["next_terminal_action"]
assert "NO_AUTOMATIONBENCH_PUBLIC600_REPEAT" in auth["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_V5_HLE_COMPRESSED_FRONTIER_PUBLIC_RUNNER_RESULT",
 "status":"PASS__CURRENT_BASE_570E6581__V5_PRESERVED__ROOT1_ZERO__ROOT3_ZERO_RUNNABLE__HLE_ADAPTER_DISCHARGED_ONE_SIDED__AUTOMATIONBENCH_SEARCH_DELETED__CHARTOGRAPHY_1000_CALL_ACCOUNT_RESIDUAL__OSWORLD_BOOT_AND_SOURCE_COMPRESSION_PRESERVED__5_OF_19__12_OF_38__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
