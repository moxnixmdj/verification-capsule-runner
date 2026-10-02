import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

p=Path("verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6.json")
payload=json.loads(p.read_text())
out=evaluate(payload)
assert len(payload["obligations"]) == 12, len(payload["obligations"])
assert out["status"] == "COMPLETE", out
assert out["global_uncovered_obligations"] == [], out
blocked=out["blocked_route_verdicts"]
assert len(blocked) == 14, len(blocked)
assert all(row["redundant"] is True and row["uncovered_obligations"] == [] for row in blocked), blocked
assert "ADMITTED_CAD_T0_ROUTE_SPECIFIC_TERMINAL_ROUTE" in out["admissible_routes"], out
assert "ADMITTED_SACCR_T1_ROUTE_SPECIFIC_TERMINAL_ROUTE" in out["admissible_routes"], out
assert out["pending_terminal_result_routes"] == [], out
print(json.dumps(out,indent=2,sort_keys=True))
