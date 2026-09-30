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

def check(cond,label,detail=None):
    if not cond:
        raise AssertionError(label + ((":"+repr(detail)) if detail is not None else ""))

# Authored tests are useful regression evidence, but the fresh cases below are the independent oracle.
proc=subprocess.run(
    [sys.executable,"canonical/tests/test_broad_objective_semantic_decomposition.py"],
    cwd=ROOT,text=True,capture_output=True
)
check(proc.returncode==0,"AUTHORED_REGRESSION_FAILED",proc.stdout[-2000:]+proc.stderr[-2000:])

g=load("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","pr474_grounding")
d=load("canonical/runtime/bound_capabilities/broad_objective_decompose.py","pr474_broad")

roles=[
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION",
]

http2=(
    "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than "
    "the protocol's default initial stream flow-control window. Use authoritative primary technical "
    "evidence and a real executable check. Autonomously discover and verify the relevant specification, "
    "determine how to extract and interpret the required limits, choose and run a zero-cost verification "
    "method, identify material protocol-scope or interpretation limitations, independently verify the "
    "consequential result, and produce a decision-quality answer with provenance."
)
direct=d.decompose(http2)
check(direct["status"]=="DECOMPOSED","HTTP2_DIRECT_DECOMPOSITION",direct)
out=g.ground(http2,{})
check(len(out["clauses"])>1,"HTTP2_NOT_MULTICLAUSE",out)
check(out["grounded_clause_count"]==0,"HTTP2_UNEXPECTED_GROUNDING",out)
check(out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))),"HTTP2_NOT_ALL_UNRESOLVED",out)
check(out["broad_objective_decomposition_available"] is True,"HTTP2_BROAD_ROUTE_NOT_EXPOSED",out)
check([x["role"] for x in out["broad_objective_decomposition"]["roles"]]==roles,"HTTP2_ROLE_GRAPH_MISMATCH",out)
check(out["model_dependency_count"]==0,"HTTP2_MODEL_DEPENDENCY",out)

fresh=[
    "Assess whether cryogenic tank boil-off is lower under insulation regime B than regime A. Use authoritative technical evidence and independently verify the consequential comparison.",
    "Determine whether groundwater decline accelerated in the latest observation interval relative to the preceding interval. Use authoritative primary evidence and independently verify the result.",
    "Evaluate whether database checkpoint latency is higher under workload regime B than regime A. Use provenance-bearing evidence and independently verify the consequential relation.",
    "Compare reported photovoltaic module degradation rates across two operating environments. Choose and run a zero-cost verification method and preserve material scope limitations.",
]
fresh_results=[]
for i,goal in enumerate(fresh):
    r=g.ground(goal,{})
    check(len(r["clauses"])>1,f"FRESH_{i}_NOT_MULTICLAUSE",r)
    check(r["grounded_clause_count"]==0,f"FRESH_{i}_UNEXPECTED_GROUNDING",r)
    check(r["broad_objective_decomposition_available"] is True,f"FRESH_{i}_BROAD_ROUTE_NOT_EXPOSED",r)
    check(r["broad_objective_decomposition"]["status"]=="DECOMPOSED",f"FRESH_{i}_NOT_DECOMPOSED",r)
    check(r["broad_objective_decomposition"]["invented_source_urls"]==[],f"FRESH_{i}_INVENTED_URL",r)
    check(r["broad_objective_decomposition"]["invented_facts"]==[],f"FRESH_{i}_INVENTED_FACT",r)
    fresh_results.append({"index":i,"clauses":len(r["clauses"]),"status":"PASS"})

# Generic method-selection wording must NOT become an explicit recipe.
generic=(
    "Assess whether two operating regimes differ. Choose and run a zero-cost verification method. "
    "Independently verify the consequential result."
)
check(d.decompose(generic)["status"]=="DECOMPOSED","GENERIC_RUN_METHOD_WRONGLY_REJECTED",d.decompose(generic))

# Explicit recipes must remain fail closed.
negative_controls=[
    "Assess whether two values differ using https://example.com/data and extract JSON path value.",
    "Assess whether two values differ. Run python verify_values.py",
    "Assess whether two values differ. Execute ./verify_values.py",
    "Assess whether two values differ. Run /usr/bin/python verify_values.py",
    "Assess whether two values differ. Run customtool --verify values.json",
]
negative_results=[]
for i,goal in enumerate(negative_controls):
    r=d.decompose(goal)
    check(r["status"]=="UNSUPPORTED",f"EXPLICIT_RECIPE_{i}_WAS_ADMITTED",r)
    check(r.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",f"EXPLICIT_RECIPE_{i}_WRONG_REASON",r)
    negative_results.append({"index":i,"status":"PASS"})

# Partial grounding must suppress whole-goal broad fallback.
registry={
  "checksum.verify.synthetic":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["checksum integrity verification"],
    "requires":[],
    "keywords":["checksum","integrity","verify"],
    "source":{"type":"independent_qualification_fixture"}
  }
}
partial=g.ground(
    "Assess checksum integrity. Verify checksum integrity. Determine whether an unrelated metric differs.",
    registry
)
check(partial["grounded_clause_count"]>0,"PARTIAL_GROUNDING_NOT_ESTABLISHED",partial)
check(partial["broad_objective_decomposition"] is None,"PARTIAL_GROUNDING_TRIGGERED_WHOLE_GOAL_BROAD",partial)
check(partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,"PARTIAL_GROUNDING_POLICY_BROKEN",partial)

# Non-broad command-oriented artifact work remains non-broad.
non_broad=g.ground("Create output.json with one record. Verify the file exists.",{})
check(non_broad["broad_objective_decomposition"] is None,"NON_BROAD_COMMAND_REINTERPRETED",non_broad)

receipt={
  "schema":"PR474_INDEPENDENT_BROAD_ROUTING_QUALIFICATION_V1",
  "status":"PASS",
  "brain_pr":474,
  "candidate_grounding_blob":"46e8e7466479ea298c34e5fa682d49c374510ce9",
  "candidate_broad_blob":"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
  "candidate_test_blob":"2df7c6ec85083458a69675f6ff86eca9c00ea278",
  "exact_http2_preserved_input":"PASS",
  "fresh_cross_domain_cases":fresh_results,
  "generic_method_language":"PASS",
  "explicit_recipe_negative_controls":negative_results,
  "partial_grounding_preservation":"PASS",
  "non_broad_fail_closed":"PASS",
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "parent_task_execution":False,
}
(ROOT/"pr474_broad_routing_qualification.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
