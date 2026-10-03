#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "current":("subjects/terminal_scheduling_current_authority_v1.json","04f0ee3cd64c3f77b29ece159ac9a35eae47a9dc"),
 "active":("subjects/terminal_scheduling_v9_active_authority.json","0637e90ed6f81592339b643bde148129494ccd2f"),
 "verification":("subjects/terminal_scheduling_v9_active_authority_verification.json","06cc1f4d4e695a6a47c26e1828607750a58088d4"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]; q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())
c=load("current"); a=load("active"); v=load("verification")
assert c["current_authority"]["git_blob_sha"]==FILES["active"][1]
assert c["independent_verification"]["git_blob_sha"]==FILES["verification"][1]
assert c["independent_verification"]["conclusion"]=="success"
assert v["independent_runner"]["conclusion"]=="success"
assert v["verified"]["tool_discovery_retrieval_authority_mandatory"] is True
assert c["live_world"]["registry_predicates"]==38
assert c["live_world"]["proved_predicates"]==11
assert c["live_world"]["unresolved_predicates"]==27
assert c["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert c["live_world"]["tool_learning_success_route_noninferior"]=="OPEN"
r=c["mandatory_tool_discovery_retrieval"]
assert r["mandatory"] is True
assert r["direct_bypass_allowed"] is False
assert r["stale_authority_allowed"] is False
assert r["consumed_source_epoch_replay_allowed"] is False
assert r["no_result_means_nonexistence"] is False
assert "THIS_FILE_IS_THE_SINGLE_CURRENT_SCHEDULING_AUTHORITY_POINTER" in c["hard_rules"]
assert c["execution_authority"] is False
assert c["promotion_authority"] is False
assert c["fresh_reality_authority"] is False
assert c["capability_credit_delta"]==0 and c["family_credit_delta"]==0
print("TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1_VERIFIED")
print(json.dumps({"current_blob":FILES["current"][1],"active_blob":FILES["active"][1],"verification_blob":FILES["verification"][1],"current":True,"zero_credit":True},sort_keys=True))
