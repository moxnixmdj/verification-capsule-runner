#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("oracle_"+name,p)
    if s is None or s.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

g=load("plain_goal_bound_grounding")

multi=(
    "Assess whether thermal conductivity differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Identify material scope limitations and independently verify the consequential result."
)
out=g.ground(multi,{})
assert len(out["clauses"]) >= 2, out
assert out["grounded_clause_count"] == 0, out
assert len(out["unresolved_clause_indexes"]) == len(out["clauses"]), out
assert out["broad_objective_decomposition_available"] is True, out
assert out["broad_objective_decomposition"]["status"] == "DECOMPOSED", out
assert [x["role"] for x in out["broad_objective_decomposition"]["roles"]] == [
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
], out

single="Assess whether thermal conductivity is greater in regime Alpha than regime Beta"
out=g.ground(single,{})
assert len(out["clauses"]) == 1, out
assert out["broad_objective_decomposition_available"] is True, out

unsupported="Create output.json with one record. Verify the file exists."
out=g.ground(unsupported,{})
assert out["grounded_clause_count"] == 0, out
assert out["broad_objective_decomposition_available"] is False, out
assert out["broad_objective_decomposition"] is None, out

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
out=g.ground(partial,registry)
assert out["grounded_clause_count"] >= 1, out
assert len(out["unresolved_clause_indexes"]) >= 1, out
assert out["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, out
assert out["broad_objective_decomposition_available"] is False, out
assert out["broad_objective_decomposition"] is None, out
assert out["model_dependency_count"] == 0, out

print("INDEPENDENT_MULTI_CLAUSE_BROAD_OBJECTIVE_ROUTING_PASS")
