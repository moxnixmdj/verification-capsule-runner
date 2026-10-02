from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/"verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6.json"

def verify() -> None:
    payload=json.loads(PAYLOAD.read_text(encoding="utf-8"))
    out=evaluate(payload)
    assert out["status"]=="COMPLETE", out
    assert out["global_uncovered_obligations"]==[], out
    assert out["pending_terminal_result_routes"]==[], out
    assert len(payload["obligations"])==12, len(payload["obligations"])
    blocked=[r for r in payload["routes"] if r.get("blocked") is True]
    verdicts=out["blocked_route_verdicts"]
    assert len(blocked)==14, len(blocked)
    assert len(verdicts)==14, len(verdicts)
    assert all(v["redundant"] is True for v in verdicts), verdicts
    assert all(v["uncovered_obligations"]==[] for v in verdicts), verdicts
    admissible=set(out["admissible_routes"])
    required={
        "ADMITTED_M0_PORTFOLIO_MULTIPLEX_TERMINAL_ROUTE",
        "ADMITTED_CAD_T0_ROUTE_SPECIFIC_TERMINAL_ROUTE",
        "ADMITTED_SACCR_T1_ROUTE_SPECIFIC_TERMINAL_ROUTE",
        "VERIFIED_TASK_TO_DELEGATION_GRAPH_DIRECT_PROOF",
    }
    assert required <= admissible, (required-admissible, sorted(admissible))
    assert payload["precommit_expected_check"]["active_contract_count"]==12
    assert payload["precommit_expected_check"]["global_uncovered"]==[]
    assert payload["fresh_terminal_evidence_consumed"]==0
    assert payload["incremental_spend_usd"]==0

if __name__=="__main__":
    verify()
    print("V6_SURFACE_DOMINANCE_PASS")
