#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_"+name,p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

dec=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

generic=(
    "Assess whether thermal efficiency differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost "
    "verification method, identify material scope limitations, independently verify "
    "the consequential result, and produce a decision-quality answer."
)
d=dec.decompose(generic)
assert d["status"]=="DECOMPOSED", d
g=ground.ground(generic,{})
assert len(g["clauses"])>1, g
assert g["grounded_clause_count"]==0, g
assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))), g
assert g["broad_objective_decomposition_available"] is True, g
assert g["broad_objective_decomposition"]["status"]=="DECOMPOSED", g

for concrete in (
    "Assess whether two measured values differ. Run python verify_values.py",
    "Evaluate whether outputs differ. Execute ./verify.sh",
    "Compare values using https://example.com/data",
):
    x=dec.decompose(concrete)
    assert x["status"]=="UNSUPPORTED", (concrete,x)
    assert x["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (concrete,x)

registry={
  "oracle.battery.measure":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["battery measurement"],
    "requires":[],
    "keywords":["battery","measurement"],
  }
}
partial=(
    "Assess battery measurement behavior. "
    "Investigate quux-sentinel evidence from an unrelated domain."
)
p=ground.ground(partial,registry)
assert p["grounded_clause_count"]>=1, p
assert p["broad_objective_decomposition_available"] is False, p
assert p["broad_objective_decomposition"] is None, p

single=ground.ground(
    "Compare annual launch counts in the recent five-year period with the preceding five-year period",
    {}
)
assert single["broad_objective_decomposition_available"] is True, single

print("INDEPENDENT_PR474_CORRECTED_BROAD_ROUTING_PASS")
