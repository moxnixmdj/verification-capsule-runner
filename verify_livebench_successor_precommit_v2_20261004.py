from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_successor_precommit_v2_20261004"
EXPECTED={
 "manifest":("LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json","66554061f204d8a86b37a30c84d0cf07a525a786"),
 "runtime":("livebench_if_execution_precommit_v2.py","f959a10bb7bfd91a4f01317b3e4afd957237ede2"),
 "resource":("LIVEBENCH_ZERO_CASE_RESOURCE_FIT_TRUTH_REPAIR_20261004_V1.json","8a603c1f48aad6e0fc79c2c76d2db437efde3893"),
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,(p,e) in EXPECTED.items():
    assert blob(SUB/p)==e,(k,blob(SUB/p),e)

spec=importlib.util.spec_from_file_location("precommit_v2",SUB/"livebench_if_execution_precommit_v2.py")
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
m=json.loads((SUB/"LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json").read_text())
r=json.loads((SUB/"LIVEBENCH_ZERO_CASE_RESOURCE_FIT_TRUTH_REPAIR_20261004_V1.json").read_text())

out=mod.verify_precommit_v2(m)
assert out["successor_precommit_pass"] is True,out
assert out["terminal_cases_consumed"]==0
assert out["case_reveal_authority"] is False
assert out["shadow_collection_authority"] is False
assert out["acceptance_credit_authorized"] is False

assert r["negative_run"]["conclusion"]=="failure"
assert "spacy" in r["negative_run"]["failure"]
assert r["positive_run"]["conclusion"]=="success"
assert r["positive_run"]["verified"]["terminal_cases_consumed"]==0
assert r["repair"]["added_direct_packages"]==[["spacy","3.8.16"],["en-core-web-sm","3.8.0"]]

x=json.loads(json.dumps(m))
x["environment"]["packages"]=[p for p in x["environment"]["packages"] if p[0]!="spacy"]
assert mod.verify_precommit_v2(x)["successor_precommit_pass"] is False

x=json.loads(json.dumps(m))
x["harness"]["shadow_lease_runtime_path"]="canonical/runtime/shadow_reality_lease_v1.py"
assert mod.verify_precommit_v2(x)["successor_precommit_pass"] is False

for name in ("candidate","harness","scorer","environment","policy"):
    x=json.loads(json.dumps(m)); x[name]["mutation"]="x"
    assert mod.verify_precommit_v2(x)["successor_precommit_pass"] is False,name

print(json.dumps({
 "status":"PASS",
 "exact_blob_count":3,
 "successor_precommit_pass":True,
 "historical_environment_failure_bound":True,
 "resource_fit_repair_bound":True,
 "shadow_v2_bound":True,
 "terminal_cases_consumed":0,
 "case_reveal_authority":False,
 "shadow_collection_authority":False,
 "acceptance_credit_authorized":False
},sort_keys=True))
