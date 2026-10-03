#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND={
 "canonical/action_intents/2026-10-04_ROOT2_ROUTE_COMPRESSION_V2_FINAL_INTEGRATION_V1.json":"622c6e6923192bacb9135164063a3383fc30d0d6",
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"e53337c1d403f1b251204547ba59f0a326ae7cc6",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"7e2c8dbde8369763c0f94e8bd96307ae5b265ae9",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"59242a061c35bb3cc60dbe3e31effe1da38955c6",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"fbfee45928cf67dc88ef024d4db3e945afc6271f",
}
BASE={
 "canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json":"16f82fed36c184b9630fedddebf9d8c52aa67d2d",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"5fe71dcc8a44274f2608e07a2a6c1b8dd12bd0f3",
 "canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"d451b51808b51b3c3a5ef8505be8919a6415a976",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"ca0dc02d57f72abaf726d8e18b41fc589c44344a",
}
SUPPORT={
 "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"afe7e055fbad7a04b169d2c0cac91b764ced20a8",
 "canonical/verification/HLE_OPUS55_POPULATION_ACCESS_CORRECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V2.json":"a62f0a2add46dc1fc5ee719592d929440e5522bb",
 "canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"de0c8c3045798e273e7aaba84162a920f89a43ad",
 "canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"288f0924157b0c0af0ff6bf302a56944f69f2fba",
 "canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"4290221e46c05af4c4cb4bc479c800564d9a41c2",
}
def blob(p:Path)->str:
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def check(group,sub):
 for rel,exp in group.items():
  got=blob(ROOT/sub/rel)
  assert got==exp,(sub,rel,got,exp)
def load(sub,rel):
 return json.loads((ROOT/sub/rel).read_text())

check(CAND,"candidate"); check(BASE,"base"); check(SUPPORT,"support")
intent=load("candidate","canonical/action_intents/2026-10-04_ROOT2_ROUTE_COMPRESSION_V2_FINAL_INTEGRATION_V1.json")
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
osboot=load("support","canonical/verification/OSWORLD_V21_ZERO_CASE_BOOT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
compv=load("support","canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
osv=load("support","canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

# Current-base, zero-credit transaction.
assert intent["base_commit_sha"]=="deb61749c171ee04e7f97bb4cbcb0b7d583599da"
assert intent["candidate_authority_blobs"]=={
 "root2_fixed_bar_route_inventory_v1":CAND["canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"],
 "current_zero_reality_minimum_cut_v8":CAND["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"],
 "root2_root3_minimum_execution_frontier_v1":CAND["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"],
 "current_terminal_authority_v1":CAND["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"],
}
for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert intent[k]==0,(k,intent[k])
for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
 assert intent[k] is False,(k,intent[k])

# No terminal truth/count movement.
assert auth["truth"]==bauth["truth"]
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["opus55_verified_owned"]=="5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN"
assert auth["truth"]["achieved"] is False
assert auth["atomic_acceptance_frontier"]==bauth["atomic_acceptance_frontier"]
assert auth["atomic_acceptance_frontier"]["proved"]==12
assert auth["atomic_acceptance_frontier"]["unresolved"]==26
assert auth["ownership_state"]==bauth["ownership_state"]
assert cut["exact_state"]==bcut["exact_state"]
assert front["exact_state"]==bfront["exact_state"]
assert inv["deduplication"]==binv["deduplication"]

# Root1 remains inactive; Root3 remains zero-runnable.
r1=root["roots"]["root_1_capability_missing"]
assert r1["current_positive_root1_blockers"]==[]
assert root["scheduler_policy"]["root1_currently_active"] is False
assert root["current_residual_root_partition"]["root1_positive_gap_count"]==0
r3=root["root3_current_execution_state"]
assert r3["currently_runnable_event_count"]==0
assert r3["fresh_reality_authority"] is False

# Preserve the current Root3 admissibility refinement exactly.
assert auth["sources"]["root3_scope_certificate_admissibility_refinement"]==bauth["sources"]["root3_scope_certificate_admissibility_refinement"]
assert front["authority"]["root3_scope_certificate_admissibility_refinement"]==bfront["authority"]["root3_scope_certificate_admissibility_refinement"]
assert "DERIVE_ROOT3_SCOPE_COMPLETENESS_FROM_FAMILY_ACCOUNTING_LABEL_CARDINALITY_OR_SINGLETON_FAMILY_TO_CONTRACT_MAPPING_WITHOUT_EXPLICIT_LOSSLESS_DECOMPOSITION_PROOF" in front["stale_work_forbidden"]

# Independent supporting receipts passed.
assert compv["independent_runner"]["conclusion"]=="success"
assert compv["verified"]["automationbench_public_private_nonsubstitution"] is True
assert compv["verified"]["chartography_minimum_judge_calls"]==1000
assert compv["verified"]["gemini_limits_per_project"] is True
assert compv["verified"]["gemini_actual_capacity_not_guaranteed"] is True
assert osv["independent_runner"]["conclusion"]=="success"
assert osv["verified"]["gitlab_release_revision_absent"] is True
assert hlev2["protocol_verifier"]["conclusion"]=="success"
assert hlev2["access_verifier"]["conclusion"]=="success"
assert hlev2["verified"]["frozen_population_identity"]=="FULL_HLE_NOT_HLE_DIAMOND"
assert hlev2["verified"]["frozen_population_question_count"]==2500
assert hlev2["verified"]["correct_huggingface_dataset"]=="cais/hle"
assert hlev2["verified"]["grader"]=="Claude Opus 4.6"
assert osboot["runner"]["conclusion"]=="success"
assert osboot["verified"]["kvm"] is True

routes={r["surface"]:r for r in inv["routes"]}

# AutomationBench search deletion without predicate closure.
auto=routes["AutomationBench"]
assert "SATURATED" in auto["state"]
assert auto["route_compression_v2"]["search_state"]=="SATURATED_CURRENT_BOUND_EVIDENCE"
assert "PROVE_PUBLIC_600_ABSOLUTE_ROUTE_SCOPE_SUFFICIENT" not in auto["next"]
assert any(x["class"]=="AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH" for x in inv["exhausted_or_waiting"])
assert not any(x["surface"]=="AutomationBench public 600" for x in cut["active_zero_reality_work"])
assert any(x["class"]=="AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH" for x in cut["exhausted_or_waiting"])

# Chartography exact 1000-call account boundary.
chart=routes["Chartography with tools"]
assert chart["route_compression_v2"]["exact_minimum_judge_calls"]==1000
assert chart["route_compression_v2"]["generic_public_search"]=="SATURATED"
assert chart["route_compression_v2"]["residual"]=="PROJECT_SPECIFIC_ACCOUNT_CAPACITY"
cw=next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="Chartography with tools")
assert "1000_JUDGE_CALLS" in cw and "PROJECT_SPECIFIC" in cw
assert any(x["class"]=="CHARTOGRAPHY_GENERIC_PRICE_AND_QUOTA_SEARCH" for x in cut["exhausted_or_waiting"])

# Full-HLE 2500 truth survives; Diamond cannot reappear as load-bearing population.
hle=routes["Humanity's Last Exam with tools"]
assert hle["opus55_route_truth"]["population"]=="cais/hle"
assert hle["opus55_route_truth"]["population_question_count"]==2500
assert hle["opus55_route_truth"]["vendor_grader"]=="Claude Opus 4.6"
assert hle["opus55_route_truth"]["stale_population_interpretation"].startswith("HLE_DIAMOND_1000_DELETED")
hw=next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="HLE with tools")
assert "CAIS_HLE_FULL_2500" in hw
assert "DIAMOND" not in hw
assert "USE_HLE_DIAMOND_1000_AS_FROZEN_OPUS55_67_7_POPULATION" in front["stale_work_forbidden"]

# OSWorld boot stays discharged and source graph search shrinks.
osw=routes["OSWorld 2.1 partial"]
assert "ZERO_COST_KVM_AND_PINNED_VM_BOOT_INDEPENDENT_PASS" in osw["state"]
assert osw["zero_case_boot"]["removed"]==["ZERO_COST_KVM_CARRIER","PINNED_VM_BOOT"]
assert osw["source_boundary_v1"]["gitlab_release_revision_pinned"] is False
assert "ZERO_COST_KVM_CARRIER" not in osw["next"]
assert "PINNED_VM_BOOT" not in osw["next"]
ow=next(x["work"] for x in cut["active_zero_reality_work"] if x["surface"]=="OSWorld 2.1 partial")
assert "KVM" not in ow and "VM_BOOT" not in ow
assert "HUGGINGFACE" in ow and "GITLAB" in ow

# Top authority points to exact candidate bytes and verified evidence.
assert auth["sources"]["root2_fixed_bar_route_inventory_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"]
assert auth["sources"]["root2_root3_minimum_execution_frontier_v1"]["git_blob_sha"]==CAND["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]
assert auth["sources"]["current_zero_reality_minimum_cut_v8"]["git_blob_sha"]==CAND["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"]
assert auth["sources"]["root2_route_compression_v2"]["verification_git_blob_sha"]==SUPPORT["canonical/verification/ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert auth["sources"]["osworld_v21_self_host_source_boundary"]["verification_git_blob_sha"]==SUPPORT["canonical/verification/OSWORLD_V21_SELF_HOST_SOURCE_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert auth["sources"]["hle_opus55_population_access_correction_v2"]["git_blob_sha"]==SUPPORT["canonical/verification/HLE_OPUS55_POPULATION_ACCESS_CORRECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V2.json"]

# No execution/fresh-reality/promotion authority.
for obj in (cut,front):
 assert obj["execution_authority"] is False
 assert obj["promotion_authority"] is False
 assert obj["fresh_reality_authority"] is False
assert "ROOT2_ONLY_LIVE_ZERO_REALITY_FRONTIER" in auth["next_terminal_action"]
assert "NO_AUTOMATIONBENCH_PUBLIC600_REPEAT" in auth["next_terminal_action"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_COMPRESSED_FRONTIER_FINAL_PUBLIC_RUNNER_RESULT",
 "status":"PASS__CURRENT_BASE_DEB61749__TRUTH_COUNTS_PRESERVED__ROOT1_ZERO__ROOT3_ZERO_RUNNABLE_AND_REFINEMENT_PRESERVED__FULL_HLE_2500__AUTOMATIONBENCH_SEARCH_DELETED__CHARTOGRAPHY_1000_CALL_ACCOUNT_RESIDUAL__OSWORLD_BOOT_AND_SOURCE_COMPRESSION_PRESERVED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
