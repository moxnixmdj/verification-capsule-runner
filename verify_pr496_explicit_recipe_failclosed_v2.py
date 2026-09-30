#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

dec=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","pr496_dec")
ground=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","pr496_ground")

def must_reject(text):
    out=dec.decompose(text)
    assert out.get("status")=="UNSUPPORTED",(text,out)
    assert out.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",(text,out)

def must_decompose(text):
    out=dec.decompose(text)
    assert out.get("status")=="DECOMPOSED",(text,out)
    assert out.get("model_dependency_count")==0,(text,out)
    return out

for text in [
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run customtool --verify values.json",
    "Investigate whether two measurements differ. Execute /opt/acme/checker --input data.bin",
    "Compare two observations. Run foo",
    "Assess whether two measurements differ. Run a verification method with python verify.py",
    "Quantify whether two regimes differ using https://example.invalid/data and extract JSON path value",
]:
    must_reject(text)

for text in [
    "Assess whether two values differ. Run a zero-cost verification method, identify material limitations, and independently verify the result.",
    "Evaluate whether two regimes differ. Execute a validation procedure, preserve provenance.",
    "Investigate whether two measurements differ. Run an independently chosen verification approach; state uncertainty.",
    "Quantify whether two measurements differ. Execute a no-cost analysis method and independently verify the consequential result.",
]:
    must_decompose(text)

objective=(
    "Assess whether thermal conductivity differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, "
    "identify material scope limitations, independently verify the consequential result, "
    "and produce a decision-quality answer with provenance."
)
direct=must_decompose(objective)
g=ground.ground(objective,{})
assert len(g.get("clauses",[]))>1,g
assert g.get("grounded_clause_count")==0,g
assert g.get("unresolved_clause_indexes")==list(range(len(g.get("clauses",[])))),g
assert g.get("broad_objective_decomposition_available") is True,g
assert (g.get("broad_objective_decomposition") or {}).get("status")=="DECOMPOSED",g
assert g.get("model_dependency_count")==0,g
print("INDEPENDENT_PR496_EXPLICIT_RECIPE_FAILCLOSED_V2_PASS")
