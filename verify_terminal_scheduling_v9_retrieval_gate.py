#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "v9":("subjects/terminal_scheduling_activation_v9.json","d3cec8d1c2b2d7343bd41883bb2557eca3fe2511"),
 "world":("subjects/current_terminal_scheduling_world_v3.json","35b8ccb4879ef7d56087eb5a119c25a8b9c6f183"),
 "world_verification":("subjects/current_terminal_scheduling_world_v3_verification.json","eb26cebccf1c692bf1fb8316e94ddbbb5c7b567a"),
 "authority":("subjects/current_terminal_authority_4_of_19.json","2560dbf990a4f39f006884a2c0d1fa7950e15795"),
 "v7":("subjects/terminal_scheduling_activation_v7.json","8ff745bf0c43def264c74c5d676e49913a288625"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]; q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())
v9=load("v9"); world=load("world"); ver=load("world_verification"); authority=load("authority"); v7=load("v7")
assert v9["candidate_world"]["git_blob_sha"]==FILES["world"][1]
assert v9["candidate_verification"]["git_blob_sha"]==FILES["world_verification"][1]
assert v9["candidate_verification"]["conclusion"]=="success"
assert v9["current_authority_binding"]["git_blob_sha"]==FILES["authority"][1]
assert v9["supersedes_for_scheduling"]["git_blob_sha"]==FILES["v7"][1]
assert authority["truth"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert v9["live_world"]["frozen_predicates"]==38
assert v9["live_world"]["proved_predicates"]==11
assert v9["live_world"]["unresolved_predicates"]==27
assert v9["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert v9["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
assert v9["live_world"]["tool_discovery_retrieval_gate_required"] is True
assert v9["live_world"]["tool_discovery_retrieval_gate_pass"] is True
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["verified"]["tool_discovery_retrieval_gate_pass"] is True
assert ver["verified"]["second_tool_discovery_action_bypass_fails_closed"] is True
assert "ALL_LIVE_TOOL_DISCOVERY_RETRIEVAL_MUST_PASS_THE_EXACT_VERIFIED_V2_AUTHORITY_GATE" in v9["retrieval_law"]
assert v9["execution_authority"] is False
assert v9["promotion_authority"] is False
assert v9["fresh_reality_authority"] is False
assert v9["capability_credit_delta"]==0 and v9["family_credit_delta"]==0
print("TERMINAL_SCHEDULING_V9_RETRIEVAL_GATE_VERIFIED")
print(json.dumps({"v9_blob":FILES["v9"][1],"world_blob":FILES["world"][1],"verification_blob":FILES["world_verification"][1],"authority_blob":FILES["authority"][1],"v7_blob":FILES["v7"][1],"zero_credit":True},sort_keys=True))
