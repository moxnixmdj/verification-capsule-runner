from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
 "canonical/tests/test_trajectory_failure_typed_ir_v5.py":"abc87ada119e42b720af5fb0f472816df975bc25",
 "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json":"26cd9f4c626d4754200c64c3f298383580d67c14",
}

def blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,sha in EXPECTED.items():
 got=blob(ROOT/rel)
 assert got==sha,(rel,got,sha)

gov=json.loads((ROOT/"canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json").read_text())
assert gov["scope"]["cross_product_case_count"]==192
assert "SCOPE" in gov["scope"]["mechanism_classes"]
assert set(gov["residuals_targeted"])=={
 "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
 "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
for key in [
 "ZERO_TERMINAL_REPLAY","ZERO_NEW_REALITY",
 "ZERO_CAPABILITY_AND_FAMILY_CREDIT_UNTIL_INDEPENDENTLY_VERIFIED_AND_RECONCILED",
]:
 assert key in gov["hard_rules"],key
assert gov["capability_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

env=dict(os.environ)
env["PYTHONPATH"]=str(ROOT)
cp=subprocess.run(
 [sys.executable,"-m","unittest","canonical.tests.test_trajectory_failure_typed_ir_v5","-v"],
 cwd=ROOT,env=env,text=True,capture_output=True
)
print(cp.stdout)
print(cp.stderr,file=sys.stderr)
assert cp.returncode==0,cp.returncode

sys.path.insert(0,str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

cases=proof.suite_cases()
assert len(cases)==192
scope_cases=0
rescued=0
symptom_nonrescue=0
partial_interaction_nonrescue=0
oracle_isolated=0
for case in cases:
 public=proof.public_task(case)
 assert "_oracle" not in public and "_intervention_model" not in public
 assert "required_root_repairs" not in str(public)
 oracle_isolated+=1
 out=candidate.solve(public)
 verdict=proof.score_case(case,out)
 assert verdict.get("pass") is True,(case["seed"],verdict,out)
 mechanisms=case["_oracle"]["mechanisms"]
 if mechanisms["A1"][0]=="SCOPE":
  scope_cases+=1
 if case["_oracle"]["status"]!="AMBIGUOUS":
  repairs=list(out["repair_targets"])
  assert proof.evaluate_intervention(case,repairs)["rescued"] is True
  rescued+=1
  symptoms=case["_intervention_model"]["downstream_symptom_repairs"]
  if symptoms:
   assert proof.evaluate_intervention(case,symptoms)["rescued"] is False
   symptom_nonrescue+=1
  if case["_oracle"]["status"]=="INTERACTION":
   for r in repairs:
    assert proof.evaluate_intervention(case,[r])["rescued"] is False
   partial_interaction_nonrescue+=1

assert scope_cases==24,scope_cases
assert rescued==144,rescued
assert oracle_isolated==192
assert partial_interaction_nonrescue==48,partial_interaction_nonrescue
assert symptom_nonrescue>0

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":4,
 "suite_case_count":len(cases),
 "first_class_scope_case_count":scope_cases,
 "hidden_intervention_rescue_case_count":rescued,
 "oracle_isolation_case_count":oracle_isolated,
 "interaction_partial_repair_nonrescue_case_count":partial_interaction_nonrescue,
 "symptom_only_nonrescue_case_count":symptom_nonrescue,
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0,
},indent=2,sort_keys=True))
