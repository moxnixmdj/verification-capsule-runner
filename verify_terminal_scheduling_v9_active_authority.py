#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "active":("subjects/terminal_scheduling_v9_active_authority.json","0637e90ed6f81592339b643bde148129494ccd2f"),
 "v9":("subjects/terminal_scheduling_activation_v9.json","d3cec8d1c2b2d7343bd41883bb2557eca3fe2511"),
 "verification":("subjects/terminal_scheduling_v9_verification.json","2d9b221ddfff2b8c0c04a3c7121c1650e5f6ea8c"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]; q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())
a=load("active"); v9=load("v9"); ver=load("verification")
assert a["current_scheduling_authority"]["git_blob_sha"]==FILES["v9"][1]
assert a["independent_activation_verification"]["git_blob_sha"]==FILES["verification"][1]
assert a["independent_activation_verification"]["conclusion"]=="success"
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["verified"]["mandatory_tool_discovery_v2_retrieval_gate_preserved"] is True
assert a["live_world"]["frozen_predicates"]==38
assert a["live_world"]["proved_predicates"]==11
assert a["live_world"]["unresolved_predicates"]==27
assert a["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
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
print("TERMINAL_SCHEDULING_V9_ACTIVE_AUTHORITY_VERIFIED")
print(json.dumps({"active_blob":FILES["active"][1],"v9_blob":FILES["v9"][1],"verification_blob":FILES["verification"][1],"current_candidate":True,"zero_credit":True},sort_keys=True))
