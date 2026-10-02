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


# V3 global terminal surface dominance: same independently verified compiler,
# exact frozen Brain input, and all 14 named benchmark surfaces must be redundant.
v3=json.loads((ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V3.json").read_text())
out3=evaluate(v3)
assert out3["status"]=="COMPLETE", out3
assert out3["global_uncovered_obligations"]==[], out3
blocked3={x["route_id"]:x for x in out3["blocked_route_verdicts"]}
expected3={
  "SURFACE_TERMINAL_BENCH_4","SURFACE_FRONTIERCODE_V1_1","SURFACE_CURSORBENCH_4_0",
  "SURFACE_GDPVAL_AA_V2_1","SURFACE_AA_BRIEFCASE_V1_1","SURFACE_CHARTOGRAPHY",
  "SURFACE_FINANCE_ACCOUNTING_INDEX","SURFACE_FINANCE_AGENT_V2","SURFACE_AUTOMATIONBENCH",
  "SURFACE_OSWORLD_2_1","SURFACE_LIVEBENCH_IF","SURFACE_HLE_WITH_TOOLS",
  "SURFACE_TERMINAL_BENCH_SCIENCE_0_1","SURFACE_MYSTERYMECHANISM",
}
assert set(blocked3)==expected3, (sorted(blocked3), sorted(expected3))
for rid in sorted(expected3):
    assert blocked3[rid]["redundant"] is True, (rid,blocked3[rid])
    assert blocked3[rid]["uncovered_obligations"]==[], (rid,blocked3[rid])
assert out3["obligation_support"]["TASK_TO_DELEGATION_GRAPH_001"]==["VERIFIED_TASK_TO_DELEGATION_GRAPH_DIRECT_PROOF"], out3
print("GLOBAL_TERMINAL_SURFACE_DOMINANCE_V3: PASS")
