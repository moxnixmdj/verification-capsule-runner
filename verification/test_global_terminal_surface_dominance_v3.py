import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
payload=json.loads((ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V3.json").read_text())
out=evaluate(payload)

assert out["status"]=="COMPLETE", out
assert out["global_uncovered_obligations"]==[], out
blocked={x["route_id"]:x for x in out["blocked_route_verdicts"]}
expected={
  "SURFACE_TERMINAL_BENCH_4","SURFACE_FRONTIERCODE_V1_1","SURFACE_CURSORBENCH_4_0",
  "SURFACE_GDPVAL_AA_V2_1","SURFACE_AA_BRIEFCASE_V1_1","SURFACE_CHARTOGRAPHY",
  "SURFACE_FINANCE_ACCOUNTING_INDEX","SURFACE_FINANCE_AGENT_V2","SURFACE_AUTOMATIONBENCH",
  "SURFACE_OSWORLD_2_1","SURFACE_LIVEBENCH_IF","SURFACE_HLE_WITH_TOOLS",
  "SURFACE_TERMINAL_BENCH_SCIENCE_0_1","SURFACE_MYSTERYMECHANISM",
}
assert set(blocked)==expected, (sorted(blocked), sorted(expected))
for rid in sorted(expected):
    assert blocked[rid]["redundant"] is True, (rid, blocked[rid])
    assert blocked[rid]["uncovered_obligations"]==[], (rid, blocked[rid])
assert out["obligation_support"]["TASK_TO_DELEGATION_GRAPH_001"]==["VERIFIED_TASK_TO_DELEGATION_GRAPH_DIRECT_PROOF"], out
print("GLOBAL_TERMINAL_SURFACE_DOMINANCE_V3: PASS")
