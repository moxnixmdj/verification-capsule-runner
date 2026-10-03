#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json":"54be838a5a0a9698398893ad113641496d5051b8",
 "canonical/verification/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V10_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"746111757bf0c7b8c0c3e6e70a7172d798141c4c",
 "canonical/governance/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_V1.json":"b1d37d015d93eb71fba1742a498b793b5a2a4ea0",
 "canonical/verification/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"20fb5ddba2ec8ae93ab3b8543ff455236abef672",
 "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py":"73ff5863845402fdd304c0e8c64b4b1d36330f45",
 "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":"38b53147597b5457859e3b0d031168842560e3e2",
 "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1.json":"4fde285b62a3a84e7f12852d8600aecfc01bab81",
 "canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"a1bc5d4ef2a767973e48a96ed986f7181630d959"
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

actual={p:blob(ROOT/p) for p in EXPECTED}
assert actual==EXPECTED,{"expected":EXPECTED,"actual":actual}

ptr=json.loads((ROOT/"canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json").read_text())
cand=json.loads((ROOT/"canonical/verification/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V10_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())
v10v=json.loads((ROOT/"canonical/verification/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())

assert ptr["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT__RECOVERY_4_OF_19__MANDATORY_TOOL_DISCOVERY_V3_RETRIEVAL_GATE__ZERO_CREDIT"
assert ptr["current_authority"]["git_blob_sha"]==EXPECTED["canonical/governance/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_V1.json"]
assert ptr["independent_verification"]["git_blob_sha"]==EXPECTED["canonical/verification/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert ptr["independent_verification"]["conclusion"]=="success"
assert ptr["final_pointer_candidate_verification"]["git_blob_sha"]==EXPECTED["canonical/verification/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V10_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert ptr["final_pointer_candidate_verification"]["conclusion"]=="success"

assert ptr["live_world"]["registry_predicates"]==38
assert ptr["live_world"]["proved_predicates"]==11
assert ptr["live_world"]["unresolved_predicates"]==27
assert ptr["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert ptr["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"

r=ptr["mandatory_tool_discovery_retrieval"]
assert r["gate_git_blob_sha"]==EXPECTED["canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py"]
assert r["hypergraph_git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"]
assert r["v3_activation_git_blob_sha"]==EXPECTED["canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1.json"]
assert r["v3_live_gate_verification_git_blob_sha"]==EXPECTED["canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert r["mandatory"] is True
assert r["direct_bypass_allowed"] is False
assert r["stale_authority_allowed"] is False
assert r["pre_v3_epoch_exhaustion_allowed"] is False
assert r["consumed_source_epoch_replay_allowed"] is False
assert r["no_result_means_nonexistence"] is False

assert "THIS_FILE_IS_THE_SINGLE_CURRENT_SCHEDULING_AUTHORITY_POINTER" in ptr["hard_rules"]
assert "ALL_TOOL_DISCOVERY_RETRIEVAL_MUST_PASS_THE_EXACT_VERIFIED_V2_BASE_PLUS_V3_GATE" in ptr["hard_rules"]
assert "NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_SEARCH" in ptr["hard_rules"]

assert cand["independent_runner"]["conclusion"]=="success"
assert cand["verified"]["single_current_pointer_binding_pass"] is True
assert cand["verified"]["retrieval_v3_mandatory"] is True
assert cand["verified"]["pre_v3_epoch_exhaustion_forbidden"] is True
assert v10v["independent_runner"]["conclusion"]=="success"
assert v10v["verified"]["retrieval_v3_authority_mandatory"] is True

assert ptr["execution_authority"] is False
assert ptr["promotion_authority"] is False
assert ptr["fresh_reality_authority"] is False
assert ptr["capability_credit_delta"]==0
assert ptr["family_credit_delta"]==0

print("CURRENT_SCHEDULING_POINTER_V10_FINAL_VERIFIED")
print(json.dumps({
 "exact_blobs":actual,
 "single_current_pointer_active":True,
 "v10_bound":True,
 "retrieval_v3_mandatory":True,
 "pre_v3_epoch_exhaustion_forbidden":True,
 "same_epoch_replay_forbidden":True,
 "unknown_preserved":True,
 "zero_credit":True
},sort_keys=True))
