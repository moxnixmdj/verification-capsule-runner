from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in m["exact_brain_blobs"].items():
    actual=git_blob_sha(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

sys.path.insert(0,str(ROOT))
subprocess.run([
    sys.executable,"-m","py_compile",
    str(ROOT/"canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py"),
    str(ROOT/"canonical/runtime/trajectory_failure_typed_ir_proof_v5.py"),
],check=True)
subprocess.run([
    sys.executable,"-m","unittest",
    "canonical.tests.test_trajectory_failure_typed_ir_v5","-v"
],cwd=ROOT,check=True)

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

cases=proof.suite_cases()
assert len(cases)==192
failures=[]
scope_cases=[]
rescued=0
interaction_partial_rescue=0
for case in cases:
    out=candidate.solve(proof.public_task(case))
    verdict=proof.score_case(case,out)
    if verdict.get("pass") is not True:
        failures.append((case.get("seed"),verdict,out))
    mechanisms=case["_oracle"]["mechanisms"]
    if "SCOPE" in {k for ks in mechanisms.values() for k in ks}:
        scope_cases.append(case)
    if case["_oracle"]["status"]!="AMBIGUOUS":
        iv=proof.evaluate_intervention(case,out.get("repair_targets") or [])
        if iv.get("rescued") is True:
            rescued+=1
    if case["_oracle"]["status"]=="INTERACTION":
        for repair in out.get("repair_targets") or []:
            if proof.evaluate_intervention(case,[repair]).get("rescued") is True:
                interaction_partial_rescue+=1

assert failures==[],failures[:3]
assert len(scope_cases)>=24
assert {c["task"]["domain"] for c in scope_cases}==set(proof.DOMAINS)
assert {"IDENTIFIED","INTERACTION","AMBIGUOUS"} <= {c["_oracle"]["status"] for c in scope_cases}
nonamb=sum(1 for c in cases if c["_oracle"]["status"]!="AMBIGUOUS")
assert rescued==nonamb,(rescued,nonamb)
assert interaction_partial_rescue==0

gov=json.loads((ROOT/"canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json").read_text(encoding="utf-8"))
assert gov["terminal_results_replayed"]==0
assert gov["new_reality_units_consumed"]==0
assert gov["capability_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert set(gov["residuals_targeted"])=={
    "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
    "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}

print(json.dumps({
    "status":"PASS",
    "exact_brain_blob_count":len(m["exact_brain_blobs"]),
    "case_count":len(cases),
    "scope_case_count":len(scope_cases),
    "nonambiguous_rescues_verified":rescued,
    "interaction_partial_rescues":interaction_partial_rescue,
    "zero_credit":True
},indent=2,sort_keys=True))
