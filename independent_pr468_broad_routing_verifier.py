#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent

def load(rel,name):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+rel)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def check(cond,label):
    if not cond:
        raise AssertionError(label)

# Authored regressions first, but independent cases below determine this verifier's own oracle.
proc=subprocess.run(
    [sys.executable,"canonical/tests/test_broad_objective_semantic_decomposition.py"],
    cwd=ROOT,text=True,capture_output=True
)
check(proc.returncode==0,"AUTHORED_REGRESSION_FAILED:"+proc.stdout[-2000:]+proc.stderr[-2000:])

g=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","independent_grounding")

expected_roles=[
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION"
]

http2=(
    "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than "
    "the protocol's default initial stream flow-control window. Use authoritative primary technical "
    "evidence and a real executable check. Autonomously discover and verify the relevant specification, "
    "determine how to extract and interpret the required limits, choose and run a zero-cost verification "
    "method, identify material protocol-scope or interpretation limitations, independently verify the "
    "consequential result, and produce a decision-quality answer with provenance."
)
out=g.ground(http2,{})
check(len(out["clauses"])>1,"HTTP2_NOT_MULTICLAUSE")
check(out["grounded_clause_count"]==0,"HTTP2_UNEXPECTED_GROUNDING")
check(len(out["unresolved_clause_indexes"])==len(out["clauses"]),"HTTP2_NOT_ALL_UNRESOLVED")
check(out["broad_objective_decomposition_available"] is True,"HTTP2_BROAD_ROUTE_NOT_EXPOSED")
check(out["broad_objective_decomposition"]["status"]=="DECOMPOSED","HTTP2_NOT_DECOMPOSED")
check([x["role"] for x in out["broad_objective_decomposition"]["roles"]]==expected_roles,"HTTP2_ROLE_GRAPH_MISMATCH")
check(out["model_dependency_count"]==0,"HTTP2_MODEL_DEPENDENCY")

fresh=[
    (
      "Assess whether a cryogenic tank's boil-off rate is lower under one insulation regime than another. "
      "Use primary technical evidence. Independently verify the consequential comparison."
    ),
    (
      "Determine whether groundwater decline accelerated in the latest observation interval relative to the preceding interval. "
      "Use authoritative evidence. Preserve scope limitations and independently verify the result."
    ),
    (
      "Evaluate whether database checkpoint latency is higher under workload regime B than regime A. "
      "Use provenance-bearing evidence. Independently verify the consequential relation."
    ),
]
fresh_results=[]
for i,goal in enumerate(fresh):
    r=g.ground(goal,{})
    check(len(r["clauses"])>1,f"FRESH_{i}_NOT_MULTICLAUSE")
    check(r["grounded_clause_count"]==0,f"FRESH_{i}_UNEXPECTED_GROUNDING")
    check(r["broad_objective_decomposition_available"] is True,f"FRESH_{i}_BROAD_ROUTE_NOT_EXPOSED")
    check(r["broad_objective_decomposition"]["status"]=="DECOMPOSED",f"FRESH_{i}_NOT_DECOMPOSED")
    check(r["broad_objective_decomposition"]["invented_source_urls"]==[],f"FRESH_{i}_INVENTED_URL")
    check(r["broad_objective_decomposition"]["invented_facts"]==[],f"FRESH_{i}_INVENTED_FACT")
    fresh_results.append({"index":i,"clause_count":len(r["clauses"]),"status":"PASS"})

# Explicit recipes must remain fail-closed, even when multi-clause.
recipe=(
  "Assess whether two reported values differ. Use https://example.com/data and extract JSON path value. "
  "Independently verify the result."
)
r=g.ground(recipe,{})
check(r["grounded_clause_count"]==0,"RECIPE_UNEXPECTED_GROUNDING")
check(r["broad_objective_decomposition"] is None,"RECIPE_WAS_REINTERPRETED")

# Non-broad command sequences must not be reinterpreted as research objectives.
r=g.ground("Create output.json with one record. Verify the file exists.",{})
check(r["broad_objective_decomposition"] is None,"COMMAND_SEQUENCE_WAS_REINTERPRETED")

# If any clause is already grounded to a verified zero-spend capability, whole-goal broad fallback must stay disabled.
registry={
  "checksum.verify.synthetic":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["checksum integrity verification"],
    "requires":[],
    "keywords":["checksum","integrity","verify"],
    "source":{"type":"python_stdlib"}
  }
}
r=g.ground(
  "Assess checksum integrity. Verify checksum integrity. Determine whether an unrelated metric differs.",
  registry
)
check(r["grounded_clause_count"]>0,"PARTIAL_GROUNDING_NOT_ESTABLISHED")
check(r["broad_objective_decomposition"] is None,"PARTIAL_GROUNDING_WRONGLY_TRIGGERED_WHOLE_GOAL_BROAD_FALLBACK")
check(r["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,"PARTIAL_GROUNDING_POLICY_BROKEN")

# Existing one-clause broad behavior must remain intact.
r=g.ground("Compare recent launch counts with preceding launch counts",{})
check(r["broad_objective_decomposition_available"] is True,"SINGLE_CLAUSE_BROAD_REGRESSION")

receipt={
  "schema":"PR468_INDEPENDENT_BROAD_ROUTING_QUALIFICATION_V1",
  "status":"PASS",
  "brain_pr":468,
  "candidate_blob":"25738e959dec0be46058e4bd7720fb8ed1b599bb",
  "broad_decomposer_blob":"6eb2b20e860da466ad8b793c20060ded1fbf389b",
  "authored_test_blob":"e98a26325fd60990afc7b81158110c897eed6b5d",
  "exact_http2_parent_shape_status":"PASS",
  "fresh_cross_domain_status":"PASS",
  "explicit_recipe_fail_closed_status":"PASS",
  "non_broad_command_fail_closed_status":"PASS",
  "partial_grounding_preservation_status":"PASS",
  "single_clause_regression_status":"PASS",
  "fresh_results":fresh_results,
  "model_dependency_count":0,
  "incremental_spend_usd":0
}
(ROOT/"pr468_broad_routing_qualification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
