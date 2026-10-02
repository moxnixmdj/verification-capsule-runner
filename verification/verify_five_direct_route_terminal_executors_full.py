from __future__ import annotations
from collections import Counter
from canonical.runtime import direct_route_terminal_executors_v1 as ex

COMMITMENT="NONTERMINAL_PREFLIGHT_COMMITMENT_V1"
BEACON="NONTERMINAL_PREFLIGHT_BEACON_V1"

def run_all(run, count):
    rows=[run(COMMITMENT,BEACON,i) for i in range(count)]
    assert len(rows)==count
    assert all(r["pass"] for r in rows), [r for r in rows if not r["pass"]][:10]
    assert len({r["case_id"] for r in rows})==count
    assert len({r["seed"] for r in rows})==count
    return rows

def verify():
    assert ex.COUNTS=={
        ex.SA_CCR_ID:2000,
        ex.BROWSER_ID:150,
        ex.DELEGATION_ID:132,
        ex.TOOL_ID:180,
        ex.RESEARCH_ID:180,
    }
    saccr=run_all(ex.run_saccr_case,2000)
    browser=run_all(ex.run_browser_case,150)
    delegation=run_all(ex.run_delegation_case,132)
    tool=run_all(ex.run_tool_case,180)
    research=run_all(ex.run_research_case,180)

    assert Counter(r["case_class"] for r in browser)==Counter({
        "DIRECT":30,"NAVIGATE":30,"CONFIRM":30,"STALE_REBIND":30,"AMBIGUOUS":30
    })
    assert Counter(r["case_class"] for r in delegation)==Counter({
        "BASE_PARALLEL":12,"RESOURCE_CONFLICT":12,"WORKER_UNAVAILABLE":12,
        "STEP_UNAVAILABLE":12,"WORKER_CAPABILITY_REMOVED":12,"RESOURCE_CAPACITY_CHANGED":12,
        "CHAIN":12,"FORK_JOIN":12,"FANOUT_JOIN":12,"DUAL_ROOT_FANIN":12,"ALTERNATIVE_PLAN":12
    })
    assert Counter(r["case_class"] for r in tool)==Counter({
        "NO_CHANGE":30,"SELECTED_TOOL_LOSES_CAPABILITY":30,"CHEAPER_TOOL_GAINS_CAPABILITY":30,
        "CHEAPER_TOOL_UNAVAILABLE":30,"CHEAPER_TOOL_UNAUTHORIZED":30,"NO_SUFFICIENT_ROUTE":30
    })
    assert Counter(r["case_class"] for r in research)==Counter({
        "biology":30,"finance":30,"systems":30,"law":30,"energy":30,"materials":30
    })
    assert all("case_class" not in r for r in saccr)

if __name__=="__main__":
    verify()
    print("FIVE_DIRECT_ROUTE_FULL_NONTERMINAL_PREFLIGHT_PASS")
