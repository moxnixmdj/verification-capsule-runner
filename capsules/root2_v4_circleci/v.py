import hashlib,json
from pathlib import Path
p=Path(__file__).with_name("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json")
b=p.read_bytes()
assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="8c90a1dc4903f9b895788ff2864822d6ebc26ac9"
o=json.loads(b)
s=o["source_bindings"]["tb4_circleci_documentary_reduction"]
assert s["git_blob_sha"]=="a4fa8277482bfec8127b44682b5de2246e78259a"
assert s["verification_git_blob_sha"]=="be00fd3dbc48719b4a62e3d34eb4b266f6a2a696"
assert o["root2_touching_predicates"]==19
assert o["fresh_reality_authority"] is False
assert o["promotion_authority"] is False
assert o["accounting"]["acceptance_credit_delta"]==0
assert "CIRCLECI_FREE_PLAN_XLARGE_GEN2_DISK_RUNTIME_AND_ALLOWANCE" not in o["waiting_external_facts"]
print("PASS")
