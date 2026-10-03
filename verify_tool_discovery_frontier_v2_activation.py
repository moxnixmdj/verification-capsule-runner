#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "activation":("subjects/tool_discovery_frontier_v2_activation.json","c916c095cfb52b4b3d8dd863dfb0be0f05529f2e"),
 "frontier":("subjects/tool_discovery_frontier_v2.json","854dd675f8454be9e0ac9316fac3eefe407305c0"),
 "verification":("subjects/tool_discovery_frontier_v2_verification.json","763d57615fbab35259c9733e6bb5c7008eb21bf0"),
}
def sha(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]
 q=ROOT/p
 assert sha(q)==s,(k,sha(q),s)
 return json.loads(q.read_text())
a=load("activation"); f=load("frontier"); v=load("verification")
assert a["active_frontier"]["git_blob_sha"]==FILES["frontier"][1]
assert a["independent_verification"]["git_blob_sha"]==FILES["verification"][1]
assert a["independent_verification"]["conclusion"]=="success"
assert v["verified"]["same_minimum_residual_preserved_from_v1"] is True
assert v["verified"]["unknown_not_nonexistence_preserved"] is True
assert v["verified"]["same_github_source_epoch_repeat_disabled"] is True
assert f["residual_state_after_wake"]["state"]=="UNKNOWN__NOT_NONEXISTENCE"
assert a["operational_policy"]["current_state"]=="UNKNOWN_SCOPE_RELATION__STRICT_ACCEPTANCE_OPEN"
assert a["operational_policy"]["repeat_v1_source_epoch"] is False
assert a["operational_policy"]["repeat_v2_github_source_epoch"] is False
assert a["capability_credit_delta"]==0 and a["family_credit_delta"]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
assert "NO_RESULT_IS_NOT_NONEXISTENCE" in a["hard_rules"]
print("TOOL_DISCOVERY_FRONTIER_V2_ACTIVATION_VERIFIED")
print(json.dumps({"activation_blob":FILES["activation"][1],"frontier_blob":FILES["frontier"][1],"verification_blob":FILES["verification"][1],"active":True,"unknown_preserved":True,"zero_credit":True},sort_keys=True))
