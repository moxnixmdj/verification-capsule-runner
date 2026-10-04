import hashlib,json
from pathlib import Path

BASE=Path(__file__).parent
expected={
"ROOT2_FRONTIER_V9_ACTIVATION_V1.json":"bc15a7e14d91ffbb274fcec6cae54ff680314818",
"TERMINAL_ROOT_CAUSE_STATE_V1.json":"7664900ab5411f416afe8ecc2bcf411636c4f2d9",
"ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json":"bc4164764ed2a77b814e5bce56457b4ae21ec79d",
"CURRENT_TERMINAL_AUTHORITY_V1.json":"d533764f62b92e35020c38c4e544dba17273099f"
}
objs={}
for n,sha in expected.items():
    b=(BASE/n).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert got==sha,(n,got,sha)
    objs[n]=json.loads(b)

act=objs["ROOT2_FRONTIER_V9_ACTIVATION_V1.json"]
assert act["frontier_git_blob_sha"]=="ea5923e8a90ca115c8149266c4c37cc7e6c40a2a"
assert act["authority"]=={"scheduling":True,"effective_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}

root=objs["TERMINAL_ROOT_CAUSE_STATE_V1.json"]
ac=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ac["current_frontier_path"].endswith("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V9.json")
assert ac["current_frontier_git_blob_sha"]=="ea5923e8a90ca115c8149266c4c37cc7e6c40a2a"
assert ac["current_frontier_activation_git_blob_sha"]=="bc15a7e14d91ffbb274fcec6cae54ff680314818"
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["unresolved_atomic"]==26
assert root["accounting"]["incremental_spend_usd"]==0

mb=objs["ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json"]
mc=mb["root2_closure_controller_v2"]
assert mc["frontier_git_blob_sha"]=="ea5923e8a90ca115c8149266c4c37cc7e6c40a2a"
assert mc["frontier_activation_git_blob_sha"]=="bc15a7e14d91ffbb274fcec6cae54ff680314818"
assert mb["execution_authority"] is False and mb["promotion_authority"] is False and mb["fresh_reality_authority"] is False

term=objs["CURRENT_TERMINAL_AUTHORITY_V1.json"]
tc=term["sources"]["root2_closure_v2_current_frontier"]
assert tc["git_blob_sha"]=="ea5923e8a90ca115c8149266c4c37cc7e6c40a2a"
assert tc["activation_git_blob_sha"]=="bc15a7e14d91ffbb274fcec6cae54ff680314818"
assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False

print("PASS__EXACT_V9_ACTIVATION_PROJECTION__THREE_AUTHORITY_SURFACES_COHERENT__COUNTS_UNCHANGED__ZERO_CREDIT")
