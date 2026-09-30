#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("oracle_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

broad=load("broad_objective_decompose")
grounding=load("plain_goal_bound_grounding")

objective=(
    "Assess whether a material property differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost "
    "verification method, identify material scope limitations, independently verify "
    "the consequential result, and produce a decision-quality answer."
)
direct=broad.decompose(objective)
assert direct["status"]=="DECOMPOSED", direct
assert direct["model_dependency_count"]==0, direct

out=grounding.ground(objective,{})
assert len(out["clauses"])>1, out
assert out["grounded_clause_count"]==0, out
assert len(out["unresolved_clause_indexes"])==len(out["clauses"]), out
assert out["broad_objective_decomposition_available"] is True, out
assert out["broad_objective_decomposition"]["status"]=="DECOMPOSED", out

explicit=broad.decompose(
    "Assess whether two measured values differ. Run python verify_values.py"
)
assert explicit["status"]=="UNSUPPORTED", explicit
assert explicit["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", explicit

registry={
  "measurement.battery.voltage": {
    "status": "VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd": 0,
    "provides": ["measurement.battery.voltage"],
    "requires": [],
    "keywords": ["battery","voltage","measurement"],
    "source": {"type":"python_stdlib"}
  }
}
mixed=(
    "Assess battery voltage measurement behavior. "
    "Investigate unrelated atmospheric circulation evidence."
)
partial=grounding.ground(mixed,registry)
assert partial["grounded_clause_count"]>=1, partial
assert partial["broad_objective_decomposition_available"] is False, partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, partial

print("INDEPENDENT_BROAD_OBJECTIVE_ROUTING_AFTER_PARENT_FALSIFICATION_PASS")
