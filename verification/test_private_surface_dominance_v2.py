import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
payload=json.loads((ROOT/"verification/PRIVATE_SURFACE_DOMINANCE_INPUT_V2.json").read_text())
out=evaluate(payload)

assert out["status"]=="COMPLETE", out
assert out["global_uncovered_obligations"]==[], out
blocked={x["route_id"]:x for x in out["blocked_route_verdicts"]}
for rid in [
  "BLOCKED_FRONTIERCODE_1_1",
  "BLOCKED_CURSORBENCH_4_0",
  "BLOCKED_AA_BRIEFCASE_V1_1",
  "BLOCKED_FINANCE_AGENT_V2_PRIVATE",
  "BLOCKED_MYSTERYMECHANISM",
]:
    assert blocked[rid]["redundant"] is True, (rid,blocked[rid])
    assert blocked[rid]["uncovered_obligations"]==[], (rid,blocked[rid])
print("PRIVATE_SURFACE_DOMINANCE_V2: PASS")
