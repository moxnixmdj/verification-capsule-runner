#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
DEC=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
GROUND=ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

dec=load(DEC,"pr474_dec_independent")
ground=load(GROUND,"pr474_ground_independent")

fresh=[
    (
      "BATTERY",
      "Assess whether commercial lithium-ion battery cycle life improved faster from 2020 to 2025 than from 2015 to 2020. "
      "Use authoritative technical evidence and a real executable check. Autonomously discover and verify relevant sources, "
      "choose and run a zero-cost verification method, identify material scope limitations, independently verify the consequential result, "
      "and produce a decision-quality answer with provenance."
    ),
    (
      "ORBITAL",
      "Determine whether the orbital period of one documented near-Earth asteroid is greater than another documented near-Earth asteroid. "
      "Use authoritative primary technical evidence and a real executable check. Discover the relevant records autonomously, choose and run "
      "a zero-cost verification method, identify interpretation limitations, independently verify the consequential result, and preserve provenance."
    ),
    (
      "MATERIALS",
      "Evaluate whether the reported tensile strength of a nickel alloy at one operating temperature is lower than at another operating temperature. "
      "Use authoritative technical evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost "
      "verification method, state material limitations, independently verify the consequential result, and produce a decision-quality answer."
    ),
]

results=[]
for label,objective in fresh:
    d=dec.decompose(objective)
    if d.get("status")!="DECOMPOSED":
        raise AssertionError((label,"DECOMPOSITION_FAIL",d))
    roles=[x.get("role") for x in d.get("roles") or []]
    expected=[
      "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
      "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
    ]
    if roles!=expected:
        raise AssertionError((label,"ROLE_GRAPH_MISMATCH",roles))
    g=ground.ground(objective,{})
    if len(g.get("clauses") or []) < 2:
        raise AssertionError((label,"NOT_MULTICLAUSE",g))
    if g.get("grounded_clause_count")!=0:
        raise AssertionError((label,"UNEXPECTED_GROUNDING",g))
    if g.get("unresolved_clause_indexes")!=list(range(len(g["clauses"]))):
        raise AssertionError((label,"UNRESOLVED_SET_MISMATCH",g))
    if g.get("broad_objective_decomposition_available") is not True:
        raise AssertionError((label,"BROAD_ROUTING_NOT_ADMITTED",g))
    if (g.get("broad_objective_decomposition") or {}).get("status")!="DECOMPOSED":
        raise AssertionError((label,"BROAD_DECOMPOSITION_MISSING",g))
    results.append({"case":label,"status":"PASS","clauses":len(g["clauses"])})

for label,objective in [
    ("URL_RECIPE","Assess whether two values differ using https://example.com/data and extract JSON path value"),
    ("PYTHON_COMMAND","Assess whether two values differ. Run python verify_values.py"),
    ("SCRIPT_COMMAND","Evaluate whether two values differ. Execute ./check_values.sh"),
]:
    d=dec.decompose(objective)
    if d.get("status")!="UNSUPPORTED" or d.get("reason")!="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE":
        raise AssertionError((label,"EXPLICIT_RECIPE_NOT_REJECTED",d))
    results.append({"case":label,"status":"PASS"})

partial_goal=(
  "Assess battery cycle life trends between two time periods. "
  "Use authoritative evidence and independently verify the result."
)
registry={
 "battery.trend.verified":{
   "status":"VERIFIED_BOUND_CAPABILITY",
   "incremental_spend_usd":0,
   "provides":["battery cycle life trend analysis"],
   "requires":[],
   "keywords":["battery","cycle","life","trend"],
   "action_template":{"type":"noop"},
   "result_fields":["status"],
   "source":{"type":"python_stdlib"},
 }
}
g=ground.ground(partial_goal,registry)
if g.get("grounded_clause_count",0)<1:
    raise AssertionError(("PARTIAL_GROUNDING","EXPECTED_GROUNDED_CLAUSE",g))
if g.get("broad_objective_decomposition_available") is not False:
    raise AssertionError(("PARTIAL_GROUNDING","WHOLE_GOAL_BROAD_ROUTE_SHOULD_FAIL_CLOSED",g))
results.append({"case":"PARTIAL_GROUNDING_FAIL_CLOSED","status":"PASS"})

report={
 "schema":"PROJECT_BRAIN_PR474_BROAD_ROUTING_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":474,
 "producer_blobs":{
   "broad_objective_decompose":"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
   "plain_goal_bound_grounding":"46e8e7466479ea298c34e5fa682d49c374510ce9",
 },
 "fresh_cases":results,
 "parent_task_execution":False,
 "http2_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0,
}
path=ROOT/"pr474-broad-routing-independent-report.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
