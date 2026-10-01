#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
CAP=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=CAP/(name+".py")
    s=importlib.util.spec_from_file_location("pr474_"+name,p)
    if s is None or s.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

dec=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

spent=(
    "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater "
    "than the protocol's default initial stream flow-control window. Use authoritative primary "
    "technical evidence and a real executable check. Autonomously discover and verify the relevant "
    "specification, determine how to extract and interpret the required limits, choose and run a "
    "zero-cost verification method, identify material protocol-scope or interpretation limitations, "
    "independently verify the consequential result, and produce a decision-quality answer with provenance."
)
d=dec.decompose(spent)
assert d["status"]=="DECOMPOSED", d
g=ground.ground(spent,{})
assert len(g["clauses"])>1, g
assert g["grounded_clause_count"]==0, g
assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))), g
assert g["broad_objective_decomposition_available"] is True, g
assert g["broad_objective_decomposition"]["status"]=="DECOMPOSED", g

generic=(
    "Assess whether a material property differs between two operating regimes. "
    "Choose and run a zero-cost verification method and independently verify the result."
)
assert dec.decompose(generic)["status"]=="DECOMPOSED"

concrete="Assess whether two measured values differ. Run python verify_values.py"
x=dec.decompose(concrete)
assert x["status"]=="UNSUPPORTED", x
assert x["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", x

registry={
  "battery.health":{
    "status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,
    "provides":["battery health analysis"],"requires":[],
    "keywords":["battery health"],"source":{"type":"python"}
  }
}
partial="Analyze battery health. Assess whether charger temperature differs between operating modes."
p=ground.ground(partial,registry)
assert p["grounded_clause_count"]>=1, p
assert p["broad_objective_decomposition_available"] is False, p
assert p["model_dependency_count"]==0, p

print("INDEPENDENT_BRAIN_PR474_BROAD_ROUTING_PASS")
