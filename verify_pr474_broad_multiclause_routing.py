#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_pr474_"+name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

grounding=load("plain_goal_bound_grounding")
decomposer=load("broad_objective_decompose")

EXPECTED_ROLES=[
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
]

fresh_cases=[
    (
      "MATERIALS",
      "Assess whether a rechargeable cell chemistry's maximum charge voltage exceeds its nominal voltage. "
      "Use authoritative primary technical evidence and a real executable check. "
      "Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, "
      "identify material scope limitations, independently verify the consequential result, and produce a "
      "decision-quality answer."
    ),
    (
      "DATABASE_SYSTEMS",
      "Determine whether a database engine's maximum page size is greater than its default page size. "
      "Use authoritative primary technical evidence and a real executable check. "
      "Identify material implementation-scope limitations and independently verify the consequential result."
    ),
    (
      "INSTRUMENTATION",
      "Evaluate whether a telescope detector's maximum sampling rate exceeds its standard operating rate. "
      "Use authoritative primary technical evidence and a real executable check. "
      "Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, "
      "and preserve material limitations and provenance."
    ),
]

observed=[]
for domain,goal in fresh_cases:
    out=grounding.ground(goal,{})
    clauses=out.get("clauses") or []
    assert len(clauses)>1, (domain,out)
    assert out.get("grounded_clause_count")==0, (domain,out)
    assert out.get("unresolved_clause_indexes")==list(range(len(clauses))), (domain,out)
    assert out.get("broad_objective_decomposition_available") is True, (domain,out)
    broad=out.get("broad_objective_decomposition") or {}
    assert broad.get("status")=="DECOMPOSED", (domain,broad)
    assert broad.get("objective")==" ".join(goal.split()), (domain,broad)
    assert [x.get("role") for x in broad.get("roles") or []]==EXPECTED_ROLES, (domain,broad)
    assert out.get("model_dependency_count")==0, (domain,out)
    assert broad.get("model_dependency_count")==0, (domain,broad)
    assert out.get("whole_goal_external_discovery_forbidden_if_any_bound_grounding") is False, (domain,out)
    observed.append({
      "domain":domain,
      "clause_count":len(clauses),
      "role_count":len(broad.get("roles") or []),
      "broad_decomposition":True,
    })

generic_method=(
  "Assess whether a material property differs between two operating regimes. "
  "Use authoritative technical evidence, choose and run a zero-cost verification method, "
  "independently verify the result, and preserve material limitations."
)
generic=decomposer.decompose(generic_method)
assert generic.get("status")=="DECOMPOSED", generic

negative_controls=[
  "Assess whether two measured values differ. Run python verify_values.py",
  "Assess whether two measured values differ. Execute ./check.sh",
  "Assess whether two measured values differ using https://example.org/spec",
]
for goal in negative_controls:
    out=decomposer.decompose(goal)
    assert out.get("status")=="UNSUPPORTED", out
    assert out.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", out

partial_registry={
  "battery.voltage.inspect.stdlib":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["battery.voltage.inspect"],
    "requires":[],
    "keywords":["battery","voltage","cell","chemistry","charge","nominal","behavior"],
    "source":{"type":"python_stdlib"},
  }
}
partial_goal=(
  "Assess battery voltage behavior. "
  "Independently verify neutrino interferometer phase drift."
)
partial=grounding.ground(partial_goal,partial_registry)
clause_count=len(partial.get("clauses") or [])
grounded_count=int(partial.get("grounded_clause_count") or 0)
assert clause_count>1, partial
assert grounded_count>=1 and grounded_count<clause_count, partial
assert partial.get("broad_objective_decomposition_available") is False, partial
assert partial.get("broad_objective_decomposition") is None, partial
assert partial.get("whole_goal_external_discovery_forbidden_if_any_bound_grounding") is True, partial

print(json.dumps({
  "schema":"PROJECT_BRAIN_PR474_BROAD_MULTICLAUSE_INDEPENDENT_ORACLE_V1",
  "status":"PASS",
  "fresh_domain_count":len(fresh_cases),
  "fresh_domains":[x[0] for x in fresh_cases],
  "generic_method_language":"PASS",
  "concrete_recipe_negative_controls":len(negative_controls),
  "partial_grounding_fail_closed":"PASS",
  "model_dependency_count":0,
  "parent_task_execution":False,
  "parent_task_replay":False,
  "observed":observed,
},sort_keys=True))
