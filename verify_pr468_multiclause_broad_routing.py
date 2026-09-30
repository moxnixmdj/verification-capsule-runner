#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"
spec=importlib.util.spec_from_file_location("independent_pr468_grounding",P)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
roles=["SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION","RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION"]
fresh=[
  "Assess whether thermal conductivity differs between two material regimes. Use authoritative primary technical evidence and a real executable check. Identify material scope limitations and independently verify the consequential result.",
  "Determine whether a measured transport coefficient changed between two operating intervals. Use authoritative technical evidence. Perform a real executable check and independently verify the consequential result."
]
for goal in fresh:
    out=mod.ground(goal,{})
    assert len(out["clauses"])>1, out
    assert out["grounded_clause_count"]==0, out
    assert len(out["unresolved_clause_indexes"])==len(out["clauses"]), out
    assert out["broad_objective_decomposition_available"] is True, out
    broad=out["broad_objective_decomposition"]
    assert broad["status"]=="DECOMPOSED", broad
    assert [x["role"] for x in broad["roles"]]==roles, broad
    assert broad["model_dependency_count"]==0, broad
unsupported=mod.ground("Create output.json with one record. Then print it.",{})
assert unsupported["broad_objective_decomposition_available"] is False, unsupported
print("INDEPENDENT_MULTI_CLAUSE_BROAD_ROUTING_PASS")
