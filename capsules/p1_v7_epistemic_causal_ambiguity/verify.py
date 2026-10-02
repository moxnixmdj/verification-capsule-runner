from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py": "02e71dd3bda1c109f6fdd90048b9615776f17779",
  "canonical/runtime/trajectory_failure_typed_ir_proof_v7.py": "f077b5fcb25c76250a8154d39ab343fd56f461ea",
  "canonical/tests/test_trajectory_failure_typed_ir_v7.py": "e6a18a6186f61974828a63fcb09e682e56ba08c7",
  "canonical/governance/P1_TYPED_EPISTEMIC_CAUSAL_ENVELOPE_V7.json": "4d98aa60bb7650201e7bd94f0acdb07a9e2b79af",
  "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py": "18d4de68ee8352410e986c318868642333ec085a",
  "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886"
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for p,sha in EXPECTED.items():
    got=blob(ROOT/p)
    assert got==sha,(p,got,sha)
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as old
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as new
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof
cases=proof.suite_cases()
assert len(cases)==240
standard=cases[:192]; nested=cases[192:]
assert len(nested)==48
for c in standard:
    out=new.solve(proof.public_task(c))
    assert proof.score_case(c,out)["pass"],(c["seed"],out)
for c in nested:
    old_out=old.solve(proof.public_task(c))
    new_out=new.solve(proof.public_task(c))
    assert old_out["status"]=="IDENTIFIED",(c["seed"],old_out)
    assert new_out["status"]=="AMBIGUOUS",(c["seed"],new_out)
    assert new_out["cause_action_ids"]==["A1","A2"]
    assert proof.score_case(c,new_out)["pass"],(c["seed"],new_out)
    a1=[f"restore:A1:{c['_oracle']['mechanisms']['A1'][0]}"]
    a2=[f"restore:A2:{c['_oracle']['mechanisms']['A2'][0]}"]
    assert proof.nested_world_rescue_vector(c,a1)==(True,False)
    assert proof.nested_world_rescue_vector(c,a2)==(False,True)
print(json.dumps({
 "status":"PASS",
 "exact_brain_blobs":EXPECTED,
 "v6_regression_cases":192,
 "nested_competing_direct_cases":48,
 "total_cases":240,
 "old_v6_nested_unique_overclaims":48,
 "v7_nested_ambiguity_passes":48,
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
