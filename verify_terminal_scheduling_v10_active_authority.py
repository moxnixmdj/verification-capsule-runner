#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_V1.json":"b1d37d015d93eb71fba1742a498b793b5a2a4ea0",
 "canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V10.json":"7b82d88f94491db17fcb8d2672a830b251f320c5",
 "canonical/verification/TERMINAL_SCHEDULING_V10_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"f7bf49299797d877fbe86ae22978b8e27959d779",
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

ptr=json.loads((ROOT/"canonical/governance/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_V1.json").read_text())
v10v=json.loads((ROOT/"canonical/verification/TERMINAL_SCHEDULING_V10_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())

assert ptr["current_scheduling_authority"]["git_blob_sha"]==EXPECTED["canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V10.json"]
assert ptr["independent_activation_verification"]["git_blob_sha"]==EXPECTED["canonical/verification/TERMINAL_SCHEDULING_V10_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert ptr["independent_activation_verification"]["conclusion"]=="success"
assert ptr["live_scheduler"]["retrieval_gate_git_blob_sha"]==EXPECTED["canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py"]
assert ptr["live_scheduler"]["action_hypergraph_git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"]
assert ptr["tool_discovery_retrieval_authority"]["activation_git_blob_sha"]==EXPECTED["canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1.json"]
assert ptr["tool_discovery_retrieval_authority"]["live_gate_verification_git_blob_sha"]==EXPECTED["canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert ptr["tool_discovery_retrieval_authority"]["mandatory"] is True
assert ptr["tool_discovery_retrieval_authority"]["direct_or_stale_bypass_allowed"] is False
assert ptr["tool_discovery_retrieval_authority"]["pre_v3_epoch_exhaustion_allowed"] is False
assert ptr["tool_discovery_retrieval_authority"]["same_consumed_source_epoch_replay_allowed"] is False
assert ptr["tool_discovery_retrieval_authority"]["no_result_means_nonexistence"] is False
assert ptr["live_world"]["frozen_predicates"]==38
assert ptr["live_world"]["proved_predicates"]==11
assert ptr["live_world"]["unresolved_predicates"]==27
assert ptr["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert ptr["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
assert ptr["execution_authority"] is False and ptr["promotion_authority"] is False
assert ptr["capability_credit_delta"]==0 and ptr["family_credit_delta"]==0

assert v10v["independent_runner"]["conclusion"]=="success"
assert v10v["verified"]["retrieval_v3_gate_mandatory"] is True
assert v10v["verified"]["unresolved_predicates"]==27

print("TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_VERIFIED")
print(json.dumps({
 "exact_blobs":actual,
 "v10_active_pointer_pass":True,
 "retrieval_v3_mandatory":True,
 "direct_bypass_forbidden":True,
 "pre_v3_epoch_exhaustion_forbidden":True,
 "zero_credit":True
},sort_keys=True))
