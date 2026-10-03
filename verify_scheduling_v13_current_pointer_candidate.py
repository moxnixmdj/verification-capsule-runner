#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/v13_current_pointer_candidate.json","a2bec35e4eb0f6ed51af6d3c49a906558c560f39"),
 "a":("subjects/v13_active_authority_for_pointer.json","9fb9897d55641aaa54d82a5740c51970e677acb0"),
 "v":("subjects/v13_active_authority_verification_for_pointer.json","e86a86a251fee63876a387a50060d88a4d26ec0e")
}
def b(q):
 x=q.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def l(k):
 p,s=F[k];q=R/p;assert b(q)==s,(k,b(q),s);return json.loads(q.read_text())
p=l("p");a=l("a");v=l("v")
assert v["independent_runner"]["conclusion"]=="success"
assert p["current_authority"]["git_blob_sha"]==F["a"][1]
assert p["independent_verification"]["git_blob_sha"]==F["v"][1]
assert p["independent_verification"]["conclusion"]=="success"
assert p["mandatory_tool_discovery_retrieval"]["authority"]=="V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE"
assert p["mandatory_tool_discovery_retrieval"]["gate_git_blob_sha"]=="c3324e574c1fafb6aaab443f49b7a9600966e754"
assert p["mandatory_tool_discovery_retrieval"]["mandatory"] is True
assert p["mandatory_tool_discovery_retrieval"]["direct_bypass_allowed"] is False
assert p["mandatory_tool_discovery_retrieval"]["failed_or_partial_source_cell_consumes_epoch"] is False
assert p["mandatory_tool_discovery_retrieval"]["consumed_source_epoch_replay_allowed"] is False
assert p["mandatory_tool_discovery_retrieval"]["no_result_means_nonexistence"] is False
assert p["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert p["live_world"]["primitive_zero_reality_work_units"]==31
assert p["execution_authority"] is False and p["promotion_authority"] is False and p["fresh_reality_authority"] is False
print("TERMINAL_SCHEDULING_V13_CURRENT_POINTER_CANDIDATE_VERIFIED")
