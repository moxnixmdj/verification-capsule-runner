#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr496_"+name,p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

broad=load("broad_objective_decompose")
ground=load("plain_goal_bound_grounding")

generic=[
    "Assess whether ceramic creep rate differs between two temperature regimes. Choose and run a zero-cost verification method, state limitations, and independently verify the result.",
    "Determine whether one stellar population is older than another. Execute a validation procedure, and independently verify the consequential result.",
    "Evaluate whether transaction latency differs across isolation regimes. Run an independently chosen verification approach; preserve provenance and limitations.",
    "Compare two atmospheric measurements. Run the verification strategy, and independently verify the result.",
]
for objective in generic:
    d=broad.decompose(objective)
    assert d["status"]=="DECOMPOSED", (objective,d)
    g=ground.ground(objective,{})
    assert g["grounded_clause_count"]==0, (objective,g)
    assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))), (objective,g)
    assert g["broad_objective_decomposition_available"] is True, (objective,g)
    assert g["model_dependency_count"]==0, (objective,g)

recipes=[
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run customtool --verify values.json",
    "Assess whether two values differ. Execute C:\\Tools\\verify.exe values.json",
    "Assess whether two values differ. Run ./verify --input values.json",
    "Assess whether two values differ. Execute bespoke_checker --mode strict",
    "Assess whether two values differ. Run a verification method with python verify.py",
    "Determine whether values differ using https://example.com/data",
    "Evaluate whether values differ. Save result.json with the answer.",
]
for objective in recipes:
    d=broad.decompose(objective)
    assert d["status"]=="UNSUPPORTED", (objective,d)
    assert d["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (objective,d)

# Partial grounding must still suppress whole-goal broad fallback.
registry={
    "battery.voltage.measurement":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "provides":["battery voltage measurement"],
        "requires":[],
        "keywords":["battery","voltage","measurement"],
        "result_fields":[],
    }
}
mixed="Assess battery voltage measurement behavior. Investigate unrelated atmospheric circulation evidence."
m=ground.ground(mixed,registry)
assert m["grounded_clause_count"]>=1, m
assert m["broad_objective_decomposition_available"] is False, m
assert m["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, m

print("PR496_EXACT_GUARDED_ADVERSARIAL_QUALIFICATION_PASS")
