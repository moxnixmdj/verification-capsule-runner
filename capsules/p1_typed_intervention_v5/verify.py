from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

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

for rel,want in EXPECTED.items():
 got=blob(ROOT/rel)
 assert got==want,(rel,got,want)

candidate_src=(ROOT/"canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py").read_text()
assert "_oracle" not in candidate_src
assert "_intervention_model" not in candidate_src
assert "trajectory_failure_typed_ir_proof_v5" not in candidate_src

gov=json.loads((ROOT/"canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json").read_text())
assert gov["scope"]["cross_product_case_count"]==192
assert "SCOPE" in gov["scope"]["mechanism_classes"]
assert set(gov["residuals_targeted"])=={
 "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
 "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
assert set(gov["counterexamples_targeted"])=={
 "V4_DROP_PROVENANCE_MUTATION_SURVIVES_SCORER",
 "TERMINAL_UNFALSIFIABLE_DIAGNOSIS_MUTATION_SURVIVES_SCORER",
}
assert gov["new_reality_units_consumed"]==0
assert gov["capability_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

subprocess.run(
 [sys.executable,"-m","unittest","canonical.tests.test_trajectory_failure_typed_ir_v5","-v"],
 cwd=ROOT,check=True
)

sys.path.insert(0,str(ROOT))
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

cases=proof.suite_cases()
passes=0
scope_cases=0
rescues=0
for case in cases:
 out=candidate.solve(proof.public_task(case))
 verdict=proof.score_case(case,out)
 assert verdict["pass"] is True,(case["seed"],verdict,out)
 passes+=1
 if case["_oracle"]["mechanisms"]["A1"][0]=="SCOPE":
  scope_cases+=1
 if out["status"] in {"IDENTIFIED","INTERACTION"}:
  assert proof.evaluate_intervention(case,out["repair_targets"])["rescued"] is True
  rescues+=1

assert passes==192
assert scope_cases==24
assert rescues==144

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "typed_case_count":passes,
 "explicit_scope_case_count":scope_cases,
 "identifiable_or_interaction_rescue_count":rescues,
 "drop_provenance_mutation_killed":True,
 "unfalsifiable_output_injection_killed":True,
 "hidden_intervention_state_candidate_visible":False,
 "new_reality_units_consumed":0,
 "credit_delta":0,
},indent=2,sort_keys=True))
