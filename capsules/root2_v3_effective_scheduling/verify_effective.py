#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/"root2_frontier_v3_current_projection"/"canonical"/"governance"

TARGETS={
 "ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json":"13bc4d661565654bba847f51ce990648d46126b4",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"e40c74ea4818ac88ccc64a016c0f71f45e62c853",
 "CURRENT_TERMINAL_AUTHORITY_V1.json":"bfe12a424164149b4c07ffc140df307797783888",
}
BASES={
 "ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json":"1d3eccffe5c15914ac1d25bec56ce4d6a3f3cc8b",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"cc87fffba6b7a967fa89fd8c8c828b2b6d842ad7",
 "CURRENT_TERMINAL_AUTHORITY_V1.json":"691f1d6f9d51fc49d281216264dbe33f41958995",
}
ALLOWED={
 "ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json":{
   "next","root2_closure_controller_v2.status",
 },
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":{
   "roots.root_2_measurement_or_comparator.active_closure_controller.status",
 },
 "CURRENT_TERMINAL_AUTHORITY_V1.json":{
   "next_terminal_action","sources.root2_closure_v2_current_frontier.status",
 },
}

def blob_sha(p:Path)->str:
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(p:Path): return json.loads(p.read_text())

def diff(a,b,path=""):
    out=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            q=f"{path}.{k}" if path else k
            if k not in a or k not in b: out.append(q)
            else: out.extend(diff(a[k],b[k],q))
        return out
    if a!=b: out.append(path)
    return out

for name,sha in BASES.items():
    assert blob_sha(BASE/name)==sha,(name,"base drift")
for name,sha in TARGETS.items():
    assert blob_sha(ROOT/name)==sha,(name,"target drift")
    changed=set(diff(load(BASE/name),load(ROOT/name)))
    assert changed==ALLOWED[name],(name,changed,ALLOWED[name])

bridge=load(ROOT/"ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
root=load(ROOT/"TERMINAL_ROOT_CAUSE_STATE_V1.json")
auth=load(ROOT/"CURRENT_TERMINAL_AUTHORITY_V1.json")

# Exact V3 pointer identity was already independently verified on the base projection.
for obj_path,obj in [
 ("bridge",bridge["root2_closure_controller_v2"]),
 ("root",root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]),
]:
    p=obj.get("frontier_path") or obj.get("current_frontier_path")
    s=obj.get("frontier_git_blob_sha") or obj.get("current_frontier_git_blob_sha")
    assert p=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json",(obj_path,p)
    assert s=="681123ef6cff3506d66af6b31b61c8bc14a8a913",(obj_path,s)

src=auth["sources"]["root2_closure_v2_current_frontier"]
assert src["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json"
assert src["git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert src["activation_git_blob_sha"]=="76d36bc34947e726502d0c8fc1dbb961d6442c88"
assert src["verification_git_blob_sha"]=="8436a9eb30312b959ba094394e60f26b4833a3a2"

# Activation is scheduling-only. No truth/credit/authority relaxation.
assert "EFFECTIVE_SCHEDULING" in bridge["root2_closure_controller_v2"]["status"]
assert "EFFECTIVE_SCHEDULING" in root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["status"]
assert "EFFECTIVE_SCHEDULING" in src["status"]
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False
assert root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["fresh_reality_authority"] is False
assert auth["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert auth["truth"]["achieved"] is False
assert auth["truth"]["opus55_verified_owned"].startswith("5/19_")
acc=root["current_acceptance"]
assert (acc["accepted_families"],acc["open_families"],acc["proved_atomic"],acc["unresolved_atomic"],acc["terminal"])==(5,14,12,26,False)
part=root["current_residual_root_partition"]
assert (part["root1_positive_gap_count"],part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(0,16,7,3)

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_V3_EFFECTIVE_SCHEDULING_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_THREE_FILE_V3_EFFECTIVE_SCHEDULING_TRANSFORM__ONLY_STATUS_AND_NEXT_ACTION_CHANGED__TERMINAL_TRUTH_PRESERVED__NO_FRESH_REALITY",
 "pass":True,
 "acceptance_credit_delta":0,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
},sort_keys=True))
