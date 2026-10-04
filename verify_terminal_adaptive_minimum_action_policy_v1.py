#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND=ROOT/"terminal_adaptive_minimum_action_policy_v1_candidate.py"
GOV=ROOT/"TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V1.json"

spec=importlib.util.spec_from_file_location("candidate", CAND)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

def A(i,targets,t,p,**kw):
    return m.Action(i,frozenset(targets),t,p,**kw)

def check():
    gov=json.loads(GOV.read_text())
    assert gov["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V1"
    s=gov["exact_live_state"]
    assert s=={
        "accepted_families":5,"open_families":14,"proved_atomic":12,
        "unresolved_atomic":26,"root1_positive_gaps":0,
        "root2_only":16,"root3_only":7,"root2_and_root3":3
    }
    assert len(gov["unresolved_predicates"])==26
    assert len(set(gov["unresolved_predicates"]))==26
    assert gov["accounting"]["incremental_spend_usd"]==0
    assert gov["execution_authority"] is False
    assert gov["promotion_authority"] is False
    assert gov["fresh_reality_authority"] is False

    dead=A("dead",{"P1"},1,0.0)
    unk=A("unknown",{"P2"},2,None)
    fresh=A("fresh",{"P3"},1,1.0,zero_reality=False)
    sup=A("sup",{"P4","P5"},2,0.8)
    sub=A("sub",{"P4"},3,0.8)
    out=m.compile_frontier([dead,unk,fresh,sup,sub],allow_fresh_reality=False)
    assert out["deleted_probability_zero"]==["dead"]
    assert "sub" in out["dominated"]
    assert [x["action_id"] for x in out["unknown_probability_preserved"]]==["unknown"]
    assert all(x["action_id"]!="fresh" for x in out["ranked_known_probability"])
    assert all(x["action_id"]!="fresh" for x in out["unknown_probability_preserved"])

    out2=m.compile_frontier([fresh],allow_fresh_reality=True)
    assert out2["ranked_known_probability"][0]["action_id"]=="fresh"

    a=A("a",{"X"},10,1.0)
    b=A("b",{"Y","Z"},10,1.0,downstream_action_deletion=2)
    assert m.priority(b)>m.priority(a)

    u=A("u",{"X","Y"},1,None)
    k=A("k",{"X"},2,0.5)
    assert not m.strictly_dominates(u,k)

    tied=m.compile_frontier([A("a",{"A"},10,1.0),A("b",{"B"},10,1.0)])
    assert m.next_actions(tied)==["a","b"]

    hard=set(out["hard_rules"])
    assert "UNKNOWN_PROBABILITY_IS_NOT_REPLACED_BY_AN_INVENTED_POINT_ESTIMATE" in hard
    assert "FRESH_REALITY_IS_FILTERED_UNLESS_EXPLICITLY_AUTHORIZED" in hard

    print(json.dumps({
        "status":"PASS",
        "candidate_schema":gov["schema"],
        "unresolved_predicates":26,
        "zero_spend":True,
        "unknown_probability_preserved":True,
        "zero_probability_deleted":True,
        "fresh_reality_guarded":True,
        "dominance_fail_closed":True
    },sort_keys=True))

if __name__=="__main__":
    check()
