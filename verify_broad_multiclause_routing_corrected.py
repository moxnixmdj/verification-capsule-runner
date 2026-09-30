#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical"/"runtime"/"bound_capabilities"

def load(filename,name):
    path=BOUND/filename
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+filename)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

dec=load("broad_objective_decompose.py","qual_broad_objective_decompose")
grounding=load("plain_goal_bound_grounding.py","qual_plain_goal_bound_grounding")

EXPECTED_ROLES=[
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
]

fresh_cases=[
    (
        "Assess whether thermal conductivity differs between two alloy processing regimes. "
        "Use authoritative technical evidence and a real executable check. "
        "Autonomously discover relevant sources, choose and run a zero-cost verification method, "
        "identify material limitations, independently verify the consequential result, and preserve provenance."
    ),
    (
        "Determine whether the orbital period reported for one satellite is greater than that reported for another. "
        "Use authoritative technical evidence and a real executable check. "
        "Discover relevant evidence, choose and run a zero-cost verification method, "
        "identify interpretation limitations, independently verify the result, and preserve provenance."
    ),
]
for objective in fresh_cases:
    direct=dec.decompose(objective)
    assert direct["status"]=="DECOMPOSED",direct
    assert [x["role"] for x in direct["roles"]]==EXPECTED_ROLES,direct
    assert direct["invented_source_urls"]==[],direct
    assert direct["invented_facts"]==[],direct
    assert direct["task_specific_literals_added"]==[],direct
    out=grounding.ground(objective,{})
    assert len(out["clauses"])>1,out
    assert out["grounded_clause_count"]==0,out
    assert out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))),out
    assert out["broad_objective_decomposition_available"] is True,out
    assert [x["role"] for x in out["broad_objective_decomposition"]["roles"]]==EXPECTED_ROLES,out
    assert out["model_dependency_count"]==0,out

generic_run=(
    "Assess whether two measured quantities differ. "
    "Choose and run a zero-cost verification method and independently verify the result."
)
assert dec.decompose(generic_run)["status"]=="DECOMPOSED"

explicit_recipes=[
    "Assess whether two measured quantities differ. Run python verify_values.py",
    "Assess whether two measured quantities differ. Execute ./verify_values.sh",
    "Determine whether values differ using https://example.com/data and extract JSON path value",
]
for objective in explicit_recipes:
    out=dec.decompose(objective)
    assert out["status"]=="UNSUPPORTED",out
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",out

partial_registry={
    "material.property.lookup":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "provides":["material property evidence"],
        "requires":[],
        "keywords":["material property"],
        "source":{"type":"bound"},
    }
}
partial_goal=(
    "Assess material property evidence. "
    "Use authoritative technical evidence and independently verify the result."
)
partial=grounding.ground(partial_goal,partial_registry)
assert partial["grounded_clause_count"]>=1,partial
assert partial["broad_objective_decomposition_available"] is False,partial
assert partial["broad_objective_decomposition"] is None,partial

print("INDEPENDENT_BROAD_MULTICLAUSE_ROUTING_QUALIFICATION_PASS")
