import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V4.json").read_text())
out=evaluate(p)
assert out["status"]=="COMPLETE", out
assert out["global_uncovered_obligations"]==[], out
blocked={x["route_id"]:x for x in out["blocked_route_verdicts"]}
assert len(blocked)==14, blocked
assert all(v["redundant"] and v["uncovered_obligations"]==[] for v in blocked.values()), blocked
assert out["obligation_support"]["SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"]==["COMPOSED_RAW_SOURCE_TO_ACCEPTANCE_TERMINAL_PROOF"], out
assert "VERIFIED_ACCEPTANCE_COMPILER_DIRECT" not in out["admissible_routes"], out
print("GLOBAL_TERMINAL_SURFACE_DOMINANCE_V4: PASS")

# independent-pr-trigger-v4
