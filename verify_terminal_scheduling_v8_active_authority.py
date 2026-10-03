#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "active":("subjects/terminal_scheduling_v8_active_authority.json","95da6ca0def18fe93f1ad29d67d01a27b31e7540"),
 "v8":("subjects/terminal_scheduling_activation_v8.json","bc1d47f5250e78f3625f258bc0320b273cdc5a67"),
 "verification":("subjects/terminal_scheduling_v8_activation_verification_bound.json","4f63b2ce18f2f6a8c0e667f562f5af946403cd79"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]
 q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())
a=load("active"); v8=load("v8"); ver=load("verification")
assert a["current_scheduling_authority"]["git_blob_sha"]==FILES["v8"][1]
assert a["independent_activation_verification"]["git_blob_sha"]==FILES["verification"][1]
assert a["independent_activation_verification"]["conclusion"]=="success"
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["verified"]["mandatory_tool_discovery_v2_retrieval_gate_preserved"] is True
assert a["live_world"]["frozen_predicates"]==38
assert a["live_world"]["proved_predicates"]==8
assert a["live_world"]["unresolved_predicates"]==30
assert a["live_world"]["opus55_acceptance"]=="3/19_PASS__16/19_OPEN"
assert a["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
r=a["tool_discovery_retrieval_authority"]
assert r["mandatory"] is True
assert r["direct_or_stale_bypass_allowed"] is False
assert r["same_consumed_source_epoch_replay_allowed"] is False
assert r["no_result_means_nonexistence"] is False
assert a["execution_authority"] is False
assert a["promotion_authority"] is False
assert a["fresh_reality_authority"] is False
assert a["capability_credit_delta"]==0 and a["family_credit_delta"]==0
print("TERMINAL_SCHEDULING_V8_ACTIVE_AUTHORITY_VERIFIED")
print(json.dumps({"active_blob":FILES["active"][1],"v8_blob":FILES["v8"][1],"verification_blob":FILES["verification"][1],"current":True,"zero_credit":True},sort_keys=True))
