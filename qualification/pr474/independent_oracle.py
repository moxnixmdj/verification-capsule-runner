#!/usr/bin/env python3
import importlib.util, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
CAND=ROOT/"canonical/runtime/bound_capabilities"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
dec=load("pr474_dec",CAND/"broad_objective_decompose.py")
ground=load("pr474_ground",CAND/"plain_goal_bound_grounding.py")
roles=["SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION","RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION"]
preserved=("Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than the protocol's default initial stream flow-control window. "
"Use authoritative primary technical evidence and a real executable check. "
"Autonomously discover and verify the relevant specification, determine how to extract and interpret the required limits, choose and run a zero-cost verification method, identify material protocol-scope or interpretation limitations, independently verify the consequential result, and produce a decision-quality answer with provenance.")
direct=dec.decompose(preserved); assert direct["status"]=="DECOMPOSED",direct
out=ground.ground(preserved,{})
assert len(out["clauses"])>1,out
assert out["grounded_clause_count"]==0,out
assert out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))),out
assert out["broad_objective_decomposition_available"] is True,out
assert [r["role"] for r in out["broad_objective_decomposition"]["roles"]]==roles,out
assert out["model_dependency_count"]==0,out
fresh=[
"Evaluate whether packet loss under congestion-control mode A is greater than under mode B. Use authoritative technical evidence and a real executable check. Autonomously discover relevant sources, choose and run a zero-cost verification method, independently verify the consequential result, and produce a decision-quality answer with provenance.",
"Assess whether thermal conductivity is lower in material state X than state Y. Use authoritative primary evidence and a real executable check. Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, identify scope limitations, independently verify the result, and produce a decision-quality answer.",
"Compare whether the documented maximum transaction identifier is greater than its default initial allocation value. Use authoritative technical evidence and a real executable check. Autonomously discover the relevant specification, choose and run a zero-cost verification method, independently verify the result, and preserve provenance."
]
for objective in fresh:
    d=dec.decompose(objective); assert d["status"]=="DECOMPOSED",(objective,d)
    g=ground.ground(objective,{})
    assert len(g["clauses"])>1,(objective,g)
    assert g["grounded_clause_count"]==0,(objective,g)
    assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))),(objective,g)
    assert g["broad_objective_decomposition_available"] is True,(objective,g)
    assert [r["role"] for r in g["broad_objective_decomposition"]["roles"]]==roles,(objective,g)
for explicit in [
"Assess whether two measured values differ. Run python verify_values.py",
"Determine whether values differ using https://example.com/data and extract JSON path value",
]:
    d=dec.decompose(explicit); assert d["status"]=="UNSUPPORTED",(explicit,d)
    assert d["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",(explicit,d)
plain=dec.decompose("Create output.json with one record"); assert plain["status"]=="UNSUPPORTED",plain
partial_registry={"HTTP2_FLOW_CONTROL_BOUND":{"status":"VERIFIED_BOUND_CAPABILITY","incremental_spend_usd":0,"provides":["http2 flow control initial stream window"],"requires":[],"keywords":["http2 flow control stream window protocol maximum permitted default initial"],"source":{"type":"independent_qualification_fixture"}}}
partial=ground.ground(preserved,partial_registry)
assert partial["grounded_clause_count"]>0,partial
assert partial["broad_objective_decomposition_available"] is False,partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,partial
print("PR474_INDEPENDENT_QUALIFICATION_PASS")
print("preserved_clause_count="+str(len(out["clauses"])))
print("fresh_case_count="+str(len(fresh)))
print("partial_grounded_clause_count="+str(partial["grounded_clause_count"]))
