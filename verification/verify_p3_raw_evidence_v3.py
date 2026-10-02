import inspect, json
from canonical.runtime import p3_information_safe_proof_suite_v3 as proof
from canonical.runtime import p3_information_safe_candidate_v3 as candidate

case=proof.generate_case(17,3)
public=proof.public_task(case)
raw=json.dumps(public,sort_keys=True).lower()
assert "_oracle" not in public
assert "hidden_support" not in raw
assert "hidden_decision" not in raw
assert '"stance"' not in raw
source=inspect.getsource(candidate)
assert "_oracle" not in source
assert "p3_information_safe_proof_suite_v3" not in source

count=0
for difficulty in range(1,6):
    for seed in range(250):
        case=proof.generate_case(seed+difficulty*10000,difficulty)
        out=candidate.solve(proof.public_task(case))
        verdict=proof.score_case(case,out)
        assert verdict["pass"], (difficulty,seed,verdict,out)
        count+=1
print("P3_RAW_EVIDENCE_V3_PASS",count)
