from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_if_thin_adapter_20261004_sol"
EXPECTED={
 "GOVERNANCE.json":"efe2c4e332bd017e2cf9c955c5db93953f2aaa0f",
 "RUNTIME.py":"f0d30b287027e62970849305cac867e891b3af85",
 "TEST.py":"4102bb562883b153ecc41940b93a51cf5fbfd582",
 "GENERIC_RUNTIME.py":"58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296",
}
def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

gov=json.loads((SUB/"GOVERNANCE.json").read_text())
assert gov["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert gov["proved_field_count"]==7
assert gov["required_field_count"]==8
assert gov["thin_adapter_fields"]["zero_incremental_spend_or_entitlement_verified"] is False
assert gov["exact_remaining_adapter_residual"]==[
 "ZERO_INCREMENTAL_SPEND_OR_ALREADY_ENTITLED_CARRIER_RECEIPT_FOR_THE_EXACT_PRECOMMITTED_BRAIN_EXECUTION"
]
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert all(v==0 for v in gov["accounting"].values())

canonical=types.ModuleType("canonical")
runtime_pkg=types.ModuleType("canonical.runtime")
canonical.runtime=runtime_pkg
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime_pkg

gspec=importlib.util.spec_from_file_location(
 "canonical.runtime.generic_precommit_isolation_theorem_v1",
 SUB/"GENERIC_RUNTIME.py"
)
generic=importlib.util.module_from_spec(gspec); assert gspec and gspec.loader
sys.modules[gspec.name]=generic
gspec.loader.exec_module(generic)

spec=importlib.util.spec_from_file_location("candidate",SUB/"RUNTIME.py")
candidate=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(candidate)

out=candidate.evaluate()
assert out["proved_field_count"]==7
assert out["required_field_count"]==8
assert out["unproved_fields"]==["zero_incremental_spend_or_entitlement_verified"]
assert out["generic_checker_missing"]==["zero_incremental_spend_or_entitlement_verified"]
assert out["thin_adapter_pass"] is False
assert out["execution_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False

for key,value in candidate.BASE_FIELDS.items():
    if key=="zero_incremental_spend_or_entitlement_verified":
        continue
    assert value is True,key
    changed=dict(candidate.BASE_FIELDS); changed[key]=False
    bad=candidate.evaluate(changed)
    assert bad["thin_adapter_pass"] is False,key
    assert key in bad["generic_checker_missing"],key

full=candidate.with_zero_spend_receipt_proved()
assert full["proved_field_count"]==8
assert full["unproved_fields"]==[]
assert full["thin_adapter_pass"] is True
assert full["execution_authority"] is False
assert full["promotion_authority"] is False
assert full["fresh_reality_authority"] is False
assert full["acceptance_credit_authorized"] is False

for x in (
 "NO_LIVEBENCH_SCORE",
 "NO_BENCHMARK_CASE_EXPOSURE",
 "NO_ZERO_SPEND_CARRIER_CLAIM",
 "NO_FULL_THIN_ADAPTER_PASS",
 "NO_FRESH_REALITY_AUTHORITY",
 "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
):
    assert x in gov["hard_nonclaims"]

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "proved_thin_adapter_fields":7,
 "required_thin_adapter_fields":8,
 "sole_residual":"zero_incremental_spend_or_entitlement_verified",
 "full_adapter_if_and_only_if_zero_spend_receipt_bound":True,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
