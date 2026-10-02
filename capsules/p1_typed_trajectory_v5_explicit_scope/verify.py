from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
M=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in M["exact_brain_blobs"].items():
    actual=blob_sha(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

subprocess.run([sys.executable,"-m","py_compile",
    str(ROOT/"canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"),
    str(ROOT/"canonical/runtime/trajectory_failure_typed_ir_proof_v5.py")],check=True)
subprocess.run([sys.executable,"-m","pytest","-q",
    str(ROOT/"canonical/tests/test_trajectory_failure_typed_ir_v5.py")],
    cwd=ROOT,check=True)

sys.path.insert(0,str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as c
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as p

cases=p.suite_cases()
assert len(cases)==192,len(cases)
assert list(p.KINDS)==M["expected_mechanism_classes"],p.KINDS
scope_cases=[]
domains=set()
patterns=set()
for case in cases:
    public=p.public_task(case)
    assert "_oracle" not in public
    out=c.solve(public)
    verdict=p.score_case(case,out)
    assert verdict["pass"],(case["seed"],case["_oracle"],out,verdict)
    if "SCOPE" in {k for ks in case["_oracle"]["mechanisms"].values() for k in ks}:
        scope_cases.append((case,out))
        domains.add(case["task"]["domain"])
        patterns.add(case["_oracle"]["status"])

assert len(scope_cases)>=24,len(scope_cases)
assert domains==set(p.DOMAINS),domains
assert patterns=={"IDENTIFIED","INTERACTION","AMBIGUOUS"},patterns
assert "SCOPE" in c.ALLOWED_KINDS

bad=p.generate_case(99123,pattern="SINGLE",domain="BROWSER",kind="SCOPE")
bad_public=p.public_task(bad)
for row in bad_public["task"]["trajectory"]:
    for check in row["checks"]:
        if check["kind"]=="SCOPE":
            check["kind"]="UNKNOWN_SCOPE_ALIAS"
out=c.solve(bad_public)
assert out["status"]=="FAIL_CLOSED",out

g=json.loads((ROOT/"canonical/governance/P1_TYPED_TRAJECTORY_V5_EXPLICIT_SCOPE_ACTIVATION_V1.json").read_text())
assert g["expected"]["cross_product_case_count"]==192
assert g["expected"]["required_new_mechanism_class"]=="SCOPE"
assert g["expected"]["residual_discharged_if_independently_verified"]==M["required_scope_residual"]
assert g["expected"]["residual_not_discharged"]==M["forbidden_rescue_credit"]
assert g["capability_credit_delta"]==0 and g["family_credit_delta"]==0
assert g["execution_authority"] is False and g["promotion_authority"] is False

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(M["exact_brain_blobs"]),
 "cross_product_case_count":len(cases),
 "scope_case_count":len(scope_cases),
 "scope_domains":sorted(domains),
 "scope_pattern_statuses":sorted(patterns),
 "explicit_scope_first_class":True,
 "heterogeneous_intervention_rescue_credit":False,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
