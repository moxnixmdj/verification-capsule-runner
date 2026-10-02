import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V4.json").read_text())
out=evaluate(p)

SPEC="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
RAW="COMPOSED_RAW_SOURCE_TO_ACCEPTANCE_TERMINAL_PROOF"

assert out["status"]=="FAIL_CLOSED_UNCOVERED_OBLIGATIONS", out
assert out["global_uncovered_obligations"]==[SPEC], out
assert out["obligation_support"][SPEC]==[], out
assert RAW not in out["admissible_routes"], out
assert out["pending_terminal_result_routes"]==[RAW], out

blocked={x["route_id"]:x for x in out["blocked_route_verdicts"]}
named={k:v for k,v in blocked.items() if k.startswith("SURFACE_")}
assert len(named)==14, sorted(named)
spec_dependent={
  "SURFACE_CURSORBENCH_4_0",
  "SURFACE_FINANCE_ACCOUNTING_INDEX",
  "SURFACE_FINANCE_AGENT_V2",
  "SURFACE_FRONTIERCODE_V1_1",
  "SURFACE_HLE_WITH_TOOLS",
  "SURFACE_LIVEBENCH_IF",
  "SURFACE_MYSTERYMECHANISM",
  "SURFACE_TERMINAL_BENCH_4",
}
for rid,row in named.items():
    if rid in spec_dependent:
        assert row["redundant"] is False, (rid,row)
        assert row["uncovered_obligations"]==[SPEC], (rid,row)
    else:
        assert row["redundant"] is True, (rid,row)
        assert row["uncovered_obligations"]==[], (rid,row)

assert blocked[RAW]["redundant"] is False, blocked[RAW]
assert blocked[RAW]["uncovered_obligations"]==[SPEC], blocked[RAW]
print("CURRENT_BRAIN_GLOBAL_TERMINAL_SURFACE_DOMINANCE_V4_FAIL_CLOSED: PASS")
