#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
CAND=ROOT/"pr474_candidate"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+str(path))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

dec=load(CAND/"broad_objective_decompose.py","pr474_oracle_dec")
ground=load(CAND/"plain_goal_bound_grounding.py","pr474_oracle_ground")

fail=[]
cases=[]

def expect(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)

fresh=[
  "Assess whether an engineered ceramic retains more than half of its room-temperature strength after sustained high-temperature exposure. Use authoritative primary technical evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, identify material scope limitations, independently verify the consequential result, and produce a decision-quality answer.",
  "Determine whether a coastal tide gauge shows a larger median annual range in the most recent five complete years than in the preceding five complete years. Use authoritative primary data, choose and run a zero-cost verification method, quantify the comparison, identify limitations, independently verify the result, and preserve provenance."
]
for i,obj in enumerate(fresh):
    d=dec.decompose(obj)
    g=ground.ground(obj,{})
    expect(f"fresh_{i}_direct",d.get("status")=="DECOMPOSED",d)
    expect(f"fresh_{i}_multiclause",len(g.get("clauses",[]))>1,g.get("clauses"))
    expect(f"fresh_{i}_all_unresolved",g.get("unresolved_clause_indexes")==list(range(len(g.get("clauses",[])))),g)
    expect(f"fresh_{i}_broad_available",g.get("broad_objective_decomposition_available") is True,g)
    expect(f"fresh_{i}_model_free",g.get("model_dependency_count")==0,g)

generic="Assess whether two operating regimes differ. Choose and run a zero-cost verification method and independently verify the consequential result."
d=dec.decompose(generic)
expect("generic_run_method_allowed",d.get("status")=="DECOMPOSED",d)

for i,obj in enumerate([
  "Assess whether two values differ. Run python verify_values.py",
  "Assess whether two values differ. Execute ./check.sh",
  "Assess whether two values differ using https://example.com/data",
  "Assess whether two values differ. Run curl https://example.com/data",
]):
    d=dec.decompose(obj)
    expect(f"concrete_recipe_{i}_rejected",d.get("status")=="UNSUPPORTED" and d.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",d)

registry={
 "BATTERY_TELEMETRY_INSPECT":{
   "status":"VERIFIED_BOUND_CAPABILITY",
   "incremental_spend_usd":0,
   "provides":["inspect battery telemetry"],
   "requires":[],
   "keywords":["battery telemetry inspect"],
   "source":{"type":"python_stdlib"}
 }
}
partial="Assess whether battery temperature is anomalous. Inspect battery telemetry."
g=ground.ground(partial,registry)
expect("partial_has_grounding",g.get("grounded_clause_count",0)>0,g)
expect("partial_suppresses_whole_goal_broad",g.get("broad_objective_decomposition_available") is False,g)

report={"schema":"BRAIN_PR474_INDEPENDENT_ORACLE_V1","status":"PASS" if not fail else "FAIL","failures":fail,"cases":cases,"model_dependency_count":0,"parent_task_executed":False}
(ROOT/"pr474-independent-oracle-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
