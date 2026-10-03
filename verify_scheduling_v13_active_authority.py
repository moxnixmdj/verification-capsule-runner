#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={"a":("subjects/v13_active_authority.json","9fb9897d55641aaa54d82a5740c51970e677acb0"),"r":("subjects/v13_candidate_verification.json","81660ef489041667b5ccc5323e82d1fb127d8efd")}
def b(p):
 x=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def l(k):
 p,s=F[k]; q=R/p; assert b(q)==s,(k,b(q),s); return json.loads(q.read_text())
a=l("a"); r=l("r")
assert r["independent_runner"]["conclusion"]=="success"
assert a["independent_verification"]["git_blob_sha"]==F["r"][1]
assert a["independent_verification"]["conclusion"]=="success"
assert a["live_scheduler"]["retrieval_gate_git_blob_sha"]=="c3324e574c1fafb6aaab443f49b7a9600966e754"
assert a["live_scheduler"]["action_hypergraph_git_blob_sha"]=="38b53147597b5457859e3b0d031168842560e3e2"
m=a["mandatory_tool_discovery_retrieval"]
assert m["authority"]=="V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE"
assert m["mandatory"] is True
assert m["failed_or_partial_cell_consumes_epoch"] is False
assert m["consumed_source_epoch_replay_allowed"] is False
assert m["no_result_means_nonexistence"] is False
assert a["live_world"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert a["live_world"]["primitive_zero_reality_work_units"]==31
assert a["execution_authority"] is False
assert a["promotion_authority"] is False
assert a["fresh_reality_authority"] is False
print("TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_VERIFIED")
