#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
TARGET=ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"

spec=importlib.util.spec_from_file_location("pr468_grounding_oracle",TARGET)
grounding=importlib.util.module_from_spec(spec)
spec.loader.exec_module(grounding)

EXPECTED=[
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
]

fresh=(
    "Evaluate whether thermal storage efficiency differs between two operating regimes. "
    "Use authoritative primary technical evidence and an executable verification. "
    "Identify material scope limitations and independently verify the consequential result."
)
out=grounding.ground(fresh,{})
assert len(out["clauses"])>1, out
assert out["grounded_clause_count"]==0, out
assert len(out["unresolved_clause_indexes"])==len(out["clauses"]), out
assert out["broad_objective_decomposition_available"] is True, out
assert [x["role"] for x in out["broad_objective_decomposition"]["roles"]]==EXPECTED, out
assert out["model_dependency_count"]==0, out

explicit=(
    "Assess whether two reported values differ. "
    "Use https://example.com/data and extract JSON path value."
)
bad=grounding.ground(explicit,{})
assert len(bad["clauses"])>1, bad
assert bad["grounded_clause_count"]==0, bad
assert bad["broad_objective_decomposition_available"] is False, bad
assert bad["broad_objective_decomposition"] is None, bad

registry={
    "decision.synthesis.typed.stdlib":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "provides":["decision.synthesis.typed"],
        "requires":[],
        "keywords":["choose","decision","route","evidence","constraints"],
    }
}
mixed=(
    "Assess whether a material property differs between operating regimes. "
    "Choose the decision route using the available evidence and constraints."
)
partial=grounding.ground(mixed,registry)
assert len(partial["clauses"])>1, partial
assert partial["grounded_clause_count"]>=1, partial
assert len(partial["unresolved_clause_indexes"])>=1, partial
assert partial["broad_objective_decomposition_available"] is False, partial
assert partial["broad_objective_decomposition"] is None, partial

print("INDEPENDENT_PR468_MULTICLAUSE_ROUTING_PASS")
