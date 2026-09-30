#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

dec=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

generic=(
    "Assess whether thermal conductivity differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost "
    "verification method, identify material scope limitations, independently verify "
    "the consequential result, and produce a decision-quality answer."
)
d=dec.decompose(generic)
assert d["status"]=="DECOMPOSED",d
g=ground.ground(generic,{})
assert len(g["clauses"])>1,g
assert g["grounded_clause_count"]==0,g
assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))),g
assert g["broad_objective_decomposition_available"] is True,g
assert g["broad_objective_decomposition"]["status"]=="DECOMPOSED",g

for concrete in (
    "Assess whether two values differ. Run python verify_values.py",
    "Assess whether two values differ. Execute bash check.sh",
    "Assess whether two values differ. Run curl https://example.com/data",
    "Assess whether two values differ using https://example.com/data",
):
    out=dec.decompose(concrete)
    assert out["status"]=="UNSUPPORTED",(concrete,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",(concrete,out)

unsupported="Create output.json with one record. Verify the file exists."
u=ground.ground(unsupported,{})
assert u["grounded_clause_count"]==0,u
assert u["broad_objective_decomposition_available"] is False,u
assert u["broad_objective_decomposition"] is None,u

registry={
  "battery.health":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["battery health analysis"],
    "requires":[],
    "keywords":["battery health"],
    "source":{"type":"python"},
  }
}
partial=(
    "Analyze battery health. "
    "Assess whether charger temperature differs between operating modes."
)
p=ground.ground(partial,registry)
assert p["grounded_clause_count"]>=1,p
assert len(p["unresolved_clause_indexes"])>=1,p
assert p["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,p
assert p["broad_objective_decomposition_available"] is False,p
assert p["broad_objective_decomposition"] is None,p
assert p["model_dependency_count"]==0,p

fresh=(
    "Evaluate whether acoustic attenuation is greater in medium Alpha than medium Beta. "
    "Use authoritative evidence and independently verify the consequential result."
)
f=ground.ground(fresh,{})
assert len(f["clauses"])>1,f
assert f["grounded_clause_count"]==0,f
assert f["unresolved_clause_indexes"]==list(range(len(f["clauses"]))),f
assert f["broad_objective_decomposition_available"] is True,f

print("INDEPENDENT_PR474_BROAD_ROUTING_PASS")
