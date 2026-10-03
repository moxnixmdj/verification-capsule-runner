from __future__ import annotations

import itertools
import json
import pathlib

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7

S="SUPPORTED"
F="UNSUPPORTED"
U="UNKNOWN"


def tool(tid,cost,safe):
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":True,
        "authorized":True,
        "epoch":0,
        "safe_probe_capabilities":["CAP_A"] if safe else [],
    }


def public(rows):
    receipts=[]
    tools=[]
    for row in rows:
        tools.append(tool(row["id"],row["cost"],row["safe"]))
        if row["state"] != U:
            receipts.append({
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":row["id"],
                "capability":"CAP_A",
                "epoch":0,
                "supported":row["state"] == S,
            })
    return {
        "required_capabilities":["CAP_A"],
        "decision_epoch":0,
        "constraint":None,
        "visible_tools":tools,
        "discovery_sources":[],
        "discovery_receipts":[],
        "prior_probe_receipts":receipts,
        "version_events":[],
    }


def oracle(rows):
    viable=[r for r in rows if r["state"] != F]
    if not viable:
        return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"}
    frontier_cost=min(r["cost"] for r in viable)
    frontier=sorted((r for r in viable if r["cost"]==frontier_cost),key=lambda r:r["id"])
    verified=[r for r in frontier if r["state"] == S]
    if verified:
        return {"action":"SELECT","tool_id":verified[0]["id"]}
    probeable=sorted((r["id"],"CAP_A") for r in frontier if r["state"] == U and r["safe"])
    if probeable:
        tid,cap=probeable[0]
        return {"action":"PROBE","tool_id":tid,"capability":cap}
    return {
        "action":"ESCALATE",
        "reason":"LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE",
        "frontier_cost":float(frontier_cost),
        "tool_ids":[r["id"] for r in frontier],
    }


def exhaustive_three_tool_oracle():
    states=[S,F,U]
    checked=0
    ids=["A","B","C"]
    for state_tuple in itertools.product(states, repeat=3):
        for safe_tuple in itertools.product([False,True], repeat=3):
            for cost_tuple in itertools.product([1,2], repeat=3):
                rows=[
                    {"id":ids[i],"cost":cost_tuple[i],"state":state_tuple[i],"safe":safe_tuple[i]}
                    for i in range(3)
                ]
                expected=oracle(rows)
                got=v7.next_action(public(rows))
                assert got == expected, (rows,expected,got)
                checked += 1
    return checked


def exact_v6_counterexample():
    rows=[
        {"id":"A_UNKNOWN","cost":1,"state":U,"safe":False},
        {"id":"Z_VERIFIED","cost":1,"state":S,"safe":True},
    ]
    p=public(rows)
    old=v6.next_action(p)
    assert old == {
        "action":"ESCALATE",
        "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
        "tool_id":"A_UNKNOWN",
    }, old
    assert v7.next_action(p) == {"action":"SELECT","tool_id":"Z_VERIFIED"}


def mixed_frontier_attack():
    rows=[
        {"id":"A_UNSAFE","cost":1,"state":U,"safe":False},
        {"id":"B_SAFE","cost":1,"state":U,"safe":True},
        {"id":"C_KNOWN","cost":2,"state":S,"safe":True},
    ]
    got=v7.next_action(public(rows))
    assert got == {"action":"PROBE","tool_id":"B_SAFE","capability":"CAP_A"}, got


def strict_cheaper_blocker_attack():
    rows=[
        {"id":"CHEAP","cost":1,"state":U,"safe":False},
        {"id":"KNOWN","cost":2,"state":S,"safe":True},
    ]
    got=v7.next_action(public(rows))
    assert got["action"]=="ESCALATE", got
    assert got["reason"]=="LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE", got
    assert got["frontier_cost"]==1.0, got


def version_restart_attack():
    rows=[{"id":"T","cost":1,"state":S,"safe":True}]
    p=public(rows)
    p["version_events"]=[{"kind":"TOOL_VERSION_CHANGED","tool_id":"T","new_epoch":1}]
    got=v7.next_action(p)
    assert got==v6.next_action(p), (got,v6.next_action(p))
    assert got["reason"]=="TOOL_VERSION_CHANGED_RESTART_EPISODE", got


def discovery_first_attack():
    latent=tool("T",1,True)
    src={
        "source_id":"S0","cost":0.0,"available":True,"authorized":True,
        "authoritative":True,"source_epoch":0,"source_digest":v5._tools_digest([latent]),
    }
    p={
        "required_capabilities":["CAP_A"],"decision_epoch":0,"constraint":None,
        "visible_tools":[],"prior_probe_receipts":[],"discovery_sources":[src],
        "discovery_receipts":[],"version_events":[],
    }
    got=v7.next_action(p)
    assert got=={"action":"DISCOVER","source_id":"S0","query":"CAP_A"}, got


def zero_credit_guards():
    gov=json.loads(pathlib.Path(
        "canonical/governance/TOOL_DISCOVERY_DYNAMIC_V7_COST_FRONTIER_REPAIR_V1.json"
    ).read_text())
    intent=json.loads(pathlib.Path(
        "canonical/action_intents/2026-10-03_TOOL_DISCOVERY_V7_COST_FRONTIER_REPAIR_V1.json"
    ).read_text())
    for obj in (gov,intent):
        assert obj["new_reality_units_consumed"]==0
        assert obj["capability_credit_delta"]==0
        assert obj["family_credit_delta"]==0
        assert obj["execution_authority"] is False
        assert obj["promotion_authority"] is False


def source_guards():
    src=pathlib.Path("canonical/runtime/tool_discovery_dynamic_candidate_v7.py").read_text()
    assert 'verified=[row for row in frontier if not row["unknown"]]' in src
    assert 'if v5._probe_allowed(row["tool"],cap):' in src
    assert '"LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE"' in src
    assert "v6.next_action(public)" in src


def main():
    checked=exhaustive_three_tool_oracle()
    exact_v6_counterexample()
    mixed_frontier_attack()
    strict_cheaper_blocker_attack()
    version_restart_attack()
    discovery_first_attack()
    zero_credit_guards()
    source_guards()
    print(json.dumps({
        "status":"PASS__INDEPENDENT_TOOL_DISCOVERY_V7_COST_FRONTIER",
        "exhaustive_three_tool_worlds":checked,
        "v6_counterexample":"REPRODUCED_AND_REPAIRED",
        "mixed_frontier":"PASS",
        "strict_cheaper_blocker":"PRESERVED",
        "version_restart":"PRESERVED",
        "discovery_first":"PRESERVED",
        "credit_delta":0,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
