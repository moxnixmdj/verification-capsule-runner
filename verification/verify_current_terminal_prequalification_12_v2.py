from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.terminal_prequalification_reducer import evaluate

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"verification/current_brain"

def verify() -> None:
    out=evaluate(FIXTURE)
    assert out["pass"] is True, out
    assert out["execution_authority"] is True, out
    assert out["authorization"]=="T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE", out
    assert out["failed_predicates"]==[], out
    assert all(v==[] for v in out["portfolio_blockers"].values()), out

    basis=json.loads((FIXTURE/"canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json").read_text())
    protocol=json.loads((FIXTURE/"canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").read_text())
    prequal=json.loads((FIXTURE/"canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").read_text())
    assert basis["admissible_frozen_terminal_route_count"]==12
    assert len(basis["contracts"])==12
    assert all(r["proof_state"]=="TERMINAL_ROUTE_FROZEN_ADMISSIBLE" and r["blockers"]==[] for r in basis["contracts"])
    assert protocol["admissible_frozen_route_count"]==12
    assert prequal["remaining_irreducible_prequalification_blockers"]==[]
    assert prequal["execution_authority"] is False  # reducer must be the first authority grant

if __name__=="__main__":
    verify()
    print("CURRENT_12_OF_12_PREQUALIFICATION_PASS")
