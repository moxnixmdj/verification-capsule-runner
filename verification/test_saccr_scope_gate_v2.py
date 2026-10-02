import json
from pathlib import Path
from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/"verification/SA_CCR_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json").read_text())
out=evaluate(data)
assert out["admissible"] is True, out
assert out["status"]=="ADMISSIBLE_SUBSTITUTION", out
assert out["required_behavior_count"]==1, out
assert out["covered_behavior_count"]==1, out
assert out["leaked_inference_ids"]==[], out
assert out["errors"]==[], out
print("SA_CCR_SCOPE_GATE_V2: PASS")
