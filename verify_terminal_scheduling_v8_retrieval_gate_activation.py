#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "v8":("subjects/terminal_scheduling_activation_v8.json","bc1d47f5250e78f3625f258bc0320b273cdc5a67"),
 "world":("subjects/current_terminal_scheduling_world_v2.json","d227569856afaf3212ddf23250134ebf56fcf079"),
 "world_verification":("subjects/current_terminal_scheduling_world_v2_verification.json","c9d926c66d50d88851a001c67009da059ce700a2"),
 "v7":("subjects/terminal_scheduling_activation_v7.json","8ff745bf0c43def264c74c5d676e49913a288625"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]
 q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())
v8=load("v8"); world=load("world"); ver=load("world_verification"); v7=load("v7")
assert v8["candidate_world"]["git_blob_sha"]==FILES["world"][1]
assert v8["candidate_verification"]["git_blob_sha"]==FILES["world_verification"][1]
assert v8["candidate_verification"]["conclusion"]=="success"
assert v8["supersedes_for_scheduling"]["git_blob_sha"]==FILES["v7"][1]
assert v8["live_world"]["frozen_predicates"]==38
assert v8["live_world"]["proved_predicates"]==8
assert v8["live_world"]["unresolved_predicates"]==30
assert v8["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
assert v8["live_world"]["tool_discovery_retrieval_gate_required"] is True
assert v8["live_world"]["tool_discovery_retrieval_gate_pass"] is True
assert "ALL_LIVE_TOOL_DISCOVERY_RETRIEVAL_MUST_PASS_THE_EXACT_VERIFIED_V2_AUTHORITY_GATE" in v8["retrieval_law"]
assert "NO_DIRECT_OR_STALE_SEARCH_PATH" in v8["retrieval_law"]
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["verified"]["tool_discovery_retrieval_gate_pass"] is True
assert ver["verified"]["second_tool_discovery_action_bypass_fails_closed"] is True
assert ver["verified"]["scheduler_call_without_gate_fails_closed"] is True
assert v8["execution_authority"] is False
assert v8["promotion_authority"] is False
assert v8["fresh_reality_authority"] is False
assert v8["capability_credit_delta"]==0 and v8["family_credit_delta"]==0
print("TERMINAL_SCHEDULING_V8_RETRIEVAL_GATE_ACTIVATION_VERIFIED")
print(json.dumps({"v8_blob":FILES["v8"][1],"world_blob":FILES["world"][1],"verification_blob":FILES["world_verification"][1],"v7_blob":FILES["v7"][1],"active_candidate":True,"zero_credit":True},sort_keys=True))
