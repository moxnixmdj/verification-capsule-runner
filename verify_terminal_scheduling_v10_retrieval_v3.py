#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V10.json":"7b82d88f94491db17fcb8d2672a830b251f320c5",
 "canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V4.json":"a17f20106cdb0518339f639b749a9a0b37f001b7",
 "canonical/verification/CURRENT_TERMINAL_SCHEDULING_WORLD_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"cc4bb19832ae7eabddc123b1e2236f7fb5c3efe1",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"f47a69253e7eb75e139b445b736d3d18b33be622",
 "canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"a1bc5d4ef2a767973e48a96ed986f7181630d959"
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
actual={p:blob(ROOT/p) for p in EXPECTED}
assert actual==EXPECTED,{"expected":EXPECTED,"actual":actual}

v10=json.loads((ROOT/"canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V10.json").read_text())
v4v=json.loads((ROOT/"canonical/verification/CURRENT_TERMINAL_SCHEDULING_WORLD_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())

assert v10["candidate_world"]["git_blob_sha"]==EXPECTED["canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V4.json"]
assert v10["candidate_verification"]["git_blob_sha"]==EXPECTED["canonical/verification/CURRENT_TERMINAL_SCHEDULING_WORLD_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert v10["candidate_verification"]["conclusion"]=="success"
assert v10["current_authority_binding"]["git_blob_sha"]==EXPECTED["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
assert v10["retrieval_v3_authority"]["live_gate_verification_git_blob_sha"]==EXPECTED["canonical/verification/RETRIEVAL_V3_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert v10["live_world"]["frozen_predicates"]==38
assert v10["live_world"]["proved_predicates"]==11
assert v10["live_world"]["unresolved_predicates"]==27
assert v10["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert v10["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
assert v10["live_world"]["tool_discovery_retrieval_gate_required"] is True
assert v10["live_world"]["tool_discovery_retrieval_gate_pass"] is True
assert v10["live_world"]["tool_discovery_retrieval_authority"]=="V3_OVER_VERIFIED_V2_BASE"
assert "NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_SEARCH" in v10["retrieval_law"]
assert v10["execution_authority"] is False
assert v10["promotion_authority"] is False
assert v10["fresh_reality_authority"] is False
assert v10["capability_credit_delta"]==0 and v10["family_credit_delta"]==0

assert v4v["independent_runner"]["conclusion"]=="success"
assert v4v["verified"]["retrieval_v3_gate_mandatory"] is True
assert v4v["verified"]["scheduler_without_retrieval_gate_fails_closed"] is True
assert v4v["verified"]["unresolved_predicates"]==27

print("TERMINAL_SCHEDULING_V10_VERIFIED")
print(json.dumps({
 "exact_blobs":actual,
 "v10_binding_pass":True,
 "current_world":"38_11_27",
 "opus55_acceptance":"4/19_PASS__15/19_OPEN",
 "retrieval_v3_mandatory":True,
 "zero_credit":True
},sort_keys=True))
