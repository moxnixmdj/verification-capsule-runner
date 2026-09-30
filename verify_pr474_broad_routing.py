#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"
REPORT=ROOT/"pr474-independent-report.json"

def load(name):
    p=CAP/(name+".py")
    s=importlib.util.spec_from_file_location("pr474_"+name,p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def req(cond,label,detail=None):
    if not cond: raise AssertionError(label+(": "+repr(detail) if detail is not None else ""))

dec=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")
cases=[
 "Assess whether thermal conductivity is greater in one operating regime than another. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, identify material limitations, independently verify the consequential result, and produce a decision-quality answer.",
 "Determine whether a telemetry rate limit is higher after a documented protocol revision than before it. Use authoritative technical evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, identify scope limitations, independently verify the consequential result, and produce a decision-quality answer.",
 "Compare two published database durability limits under their documented operating modes. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, identify scope limitations, independently verify the consequential result, and produce a decision-quality answer."
]
observed=[]
for i,goal in enumerate(cases):
    d=dec.decompose(goal)
    req(d.get("status")=="DECOMPOSED","generic method language must decompose",d)
    g=ground.ground(goal,{})
    req(len(g.get("clauses") or [])>1,"fresh case must be multiclause",g)
    req(g.get("grounded_clause_count")==0,"fresh case must have zero grounded clauses",g)
    req(g.get("unresolved_clause_indexes")==list(range(len(g.get("clauses") or []))),"all clauses must remain unresolved",g)
    req((g.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED","broad route must activate",g)
    observed.append({"case":i,"clauses":len(g["clauses"]),"status":"PASS"})
for recipe in [
 "Assess whether two values differ. Run python verify_values.py",
 "Determine whether two values differ using https://example.com/data and extract JSON path value",
]:
    d=dec.decompose(recipe)
    req(d.get("status")=="UNSUPPORTED","concrete recipe must fail closed",d)
    req(d.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE","recipe reason",d)
single=ground.ground("Compare annual launch counts in the recent five-year period with the preceding five-year period",{})
req(single.get("broad_objective_decomposition_available") is True,"single-clause regression",single)
report={"schema":"PROJECT_BRAIN_PR474_INDEPENDENT_QUALIFICATION_V1","status":"PASS","cases":observed,
"parent_task_execution":False,"spent_http2_task_replayed":False,"model_dependency_count":0,"incremental_spend_usd":0}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
