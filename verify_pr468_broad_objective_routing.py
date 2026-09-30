#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"pr468-broad-routing-independent-report.json"

def load(name):
    p=CAP/(name+".py")
    s=importlib.util.spec_from_file_location("independent_"+name,p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def require(cond,label,detail=None):
    if not cond:
        raise AssertionError(label + (": "+repr(detail) if detail is not None else ""))

def main():
    dec=load("broad_objective_decompose")
    grounding=load("plain_goal_bound_grounding")
    cases=[]

    cross_domain=(
        "Assess whether the maximum allowable thermal gradient in a reference material is greater than "
        "its ordinary operating gradient. Use authoritative primary technical evidence and a real executable check. "
        "Autonomously discover and verify the relevant technical source, determine how to extract and interpret the "
        "required limits, choose and run a zero-cost verification method, identify material scope or interpretation "
        "limitations, independently verify the consequential result, and produce a decision-quality answer with provenance."
    )
    d=dec.decompose(cross_domain)
    require(d.get("status")=="DECOMPOSED","cross-domain decomposition",d)
    g=grounding.ground(cross_domain,{})
    require(len(g.get("clauses") or [])>1,"multiclause objective required",g)
    require(g.get("grounded_clause_count")==0,"zero grounded clauses",g)
    require(len(g.get("unresolved_clause_indexes") or [])==len(g.get("clauses") or []),"all clauses unresolved",g)
    require((g.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED","broad route activated",g)
    cases.append({"id":"CROSS_DOMAIN_ALL_UNRESOLVED_MULTICLAUSE","status":"PASS","clause_count":len(g["clauses"])})

    recipe="Assess whether two measurements differ. Run python verify_values.py"
    d=dec.decompose(recipe)
    require(d.get("status")=="UNSUPPORTED","explicit recipe rejected",d)
    require(d.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE","recipe rejection reason",d)
    cases.append({"id":"EXPLICIT_COMMAND_FAIL_CLOSED","status":"PASS"})

    ordinary="Create canonical/astra_runtime/tmp/result.json with one record"
    d=dec.decompose(ordinary)
    require(d.get("status")=="UNSUPPORTED","ordinary action not research",d)
    cases.append({"id":"NON_RESEARCH_ACTION_NOT_REINTERPRETED","status":"PASS"})

    partially_groundable=(
        "Create a barcode artifact. "
        "Assess whether a protocol limit differs from its default using authoritative primary technical evidence."
    )
    registry={
      "artifact.barcode.synthetic":{
        "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
        "provides":["artifact.barcode.create"],"requires":[],
        "keywords":["barcode","artifact","create"],"source":{"type":"python_stdlib"},
        "action_template":{"type":"invoke_capability","args":{}}
      }
    }
    g=grounding.ground(partially_groundable,registry)
    require(g.get("grounded_clause_count",0)>0,"partial grounding expected",g)
    require(g.get("broad_objective_decomposition") is None,"partial grounding must not broaden whole goal",g)
    cases.append({"id":"PARTIAL_GROUNDING_PRESERVES_NO_WHOLE_GOAL_BROADENING","status":"PASS"})

    report={
      "schema":"PROJECT_BRAIN_PR468_BROAD_ROUTING_INDEPENDENT_QUALIFICATION_V1",
      "status":"PASS","cases":cases,
      "model_dependency_count":0,"incremental_spend_usd":0,
      "parent_task_execution":False,
      "spent_http2_task_replayed":False,
    }
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        report={"schema":"PROJECT_BRAIN_PR468_BROAD_ROUTING_INDEPENDENT_QUALIFICATION_V1","status":"FAIL","error_class":type(exc).__name__,"error":str(exc),"model_dependency_count":0,"incremental_spend_usd":0,"parent_task_execution":False,"spent_http2_task_replayed":False}
        REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise
