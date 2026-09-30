#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr496_"+name,p)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

broad=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

genomics=(
    "Assess whether the complete reference genome sequence length of Escherichia coli K-12 MG1655 "
    "is greater than the human mitochondrial reference genome sequence length. Use authoritative "
    "primary technical evidence and a real executable check. Autonomously discover and verify the "
    "relevant primary records, determine how to extract and interpret the two sequence lengths, "
    "choose and run a zero-cost verification method, identify material reference-version or "
    "sequence-scope limitations, independently verify the consequential result, and produce a "
    "decision-quality answer with provenance."
)
d=broad.decompose(genomics)
assert d["status"]=="DECOMPOSED", d
g=ground.ground(genomics,{})
assert len(g["clauses"])>1, g
assert g["grounded_clause_count"]==0, g
assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))), g
assert g["broad_objective_decomposition_available"] is True, g

legitimate=[
    "Assess whether two values differ. Run a zero-cost verification method, and independently verify the result.",
    "Evaluate whether two regimes differ. Execute a validation procedure; preserve material limitations.",
    "Determine whether one quantity is greater. Run an independently chosen verification approach and preserve provenance.",
    "Compare two measurements. Execute a free checking strategy, and independently verify the result.",
]
for objective in legitimate:
    out=broad.decompose(objective)
    assert out["status"]=="DECOMPOSED", (objective,out)

recipes=[
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Execute C:\\Python311\\python.exe verify_values.py",
    "Evaluate whether two regimes differ. Run customtool --verify values.json",
    "Determine whether values differ. Execute mystery-cli --input x.dat",
    "Assess whether two values differ. Run a verification method with python verify.py",
    "Assess whether two values differ. Execute a validation procedure using https://example.com/data",
    "Assess whether two values differ. Run a zero-cost verification method, and execute customtool --verify values.json",
]
for objective in recipes:
    out=broad.decompose(objective)
    assert out["status"]=="UNSUPPORTED", (objective,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (objective,out)

nonresearch=broad.decompose("Create result.json with one record")
assert nonresearch["status"]=="UNSUPPORTED", nonresearch

print("PR496_EXACT_GUARDED_INDEPENDENT_QUALIFICATION_PASS")
