from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V5.json"

def verify() -> None:
    payload=json.loads(PAYLOAD.read_text(encoding="utf-8"))
    out=evaluate(payload)
    assert out["status"]=="COMPLETE", out
    assert out["global_uncovered_obligations"]==[], out
    assert out["pending_terminal_result_routes"]==[], out
    blocked=[r for r in payload["routes"] if r.get("blocked") is True]
    verdicts=out["blocked_route_verdicts"]
    assert len(blocked)==14, len(blocked)
    assert len(verdicts)==14, len(verdicts)
    assert all(v["redundant"] is True for v in verdicts), verdicts
    assert all(v["uncovered_obligations"]==[] for v in verdicts), verdicts
    assert "ADMITTED_M0_PORTFOLIO_MULTIPLEX_TERMINAL_ROUTE" in out["admissible_routes"]
    assert payload["fresh_terminal_evidence_consumed"]==0
    assert payload["incremental_spend_usd"]==0

if __name__=="__main__":
    verify()
    print("V5_SURFACE_DOMINANCE_PASS")
