#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name,filename):
    path=BOUND/filename
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

broad=load("independent_pr474_broad","broad_objective_decompose.py")
grounding=load("independent_pr474_grounding","plain_goal_bound_grounding.py")

HTTP2_GOAL=(
    "Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater "
    "than the protocol's default initial stream flow-control window. Use authoritative primary "
    "technical evidence and a real executable check. Autonomously discover and verify the relevant "
    "specification, determine how to extract and interpret the required limits, choose and run a "
    "zero-cost verification method, identify material protocol-scope or interpretation limitations, "
    "independently verify the consequential result, and produce a decision-quality answer with provenance."
)

direct=broad.decompose(HTTP2_GOAL)
assert direct["status"]=="DECOMPOSED", direct
assert [x["role"] for x in direct["roles"]]==[
    "SOURCE_DISCOVERY",
    "EVIDENCE_ACQUISITION",
    "EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION",
    "DECISION_SYNTHESIS_AND_VERIFICATION",
], direct

http2=grounding.ground(HTTP2_GOAL,{})
assert len(http2["clauses"])>1, http2
assert http2["grounded_clause_count"]==0, http2
assert http2["unresolved_clause_indexes"]==list(range(len(http2["clauses"]))), http2
assert http2["broad_objective_decomposition_available"] is True, http2
assert http2["broad_objective_decomposition"]["status"]=="DECOMPOSED", http2
assert http2["model_dependency_count"]==0, http2

fresh=[
    (
        "Assess whether a ceramic coating retains more hardness after thermal cycling than before cycling. "
        "Use authoritative primary technical evidence and a real executable check. "
        "Choose and run a zero-cost verification method, identify material scope limitations, and independently verify the result."
    ),
    (
        "Evaluate whether packet-loss telemetry is higher during peak traffic than off-peak traffic. "
        "Use authoritative primary technical evidence and a real executable check. "
        "Choose and run a zero-cost verification method, preserve unresolved interpretation limits, and independently verify the result."
    ),
    (
        "Compare whether a database engine's documented page limit exceeds its default page setting. "
        "Use authoritative primary technical evidence and a real executable check. "
        "Choose and run a zero-cost verification method, identify scope limitations, and independently verify the result."
    ),
]
for objective in fresh:
    dec=broad.decompose(objective)
    assert dec["status"]=="DECOMPOSED", (objective,dec)
    out=grounding.ground(objective,{})
    assert len(out["clauses"])>1, out
    assert out["grounded_clause_count"]==0, out
    assert out["unresolved_clause_indexes"]==list(range(len(out["clauses"]))), out
    assert out["broad_objective_decomposition_available"] is True, out

for concrete in [
    "Assess whether two measured values differ. Run python verify_values.py",
    "Evaluate whether two values differ and execute ./verify.sh",
    "Determine whether values differ using https://example.com/data and extract JSON path value",
]:
    out=broad.decompose(concrete)
    assert out["status"]=="UNSUPPORTED", (concrete,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", (concrete,out)

ordinary=broad.decompose("Create output.json with one record")
assert ordinary["status"]=="UNSUPPORTED", ordinary

registry={
    "python.tests.audit.unittest":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "provides":["python.tests.audit"],
        "requires":[],
        "keywords":["python","tests","audit","unittest","passed","failed","skipped"],
    }
}
partial_goal=(
    "Assess whether an unknown material property changed between regimes. "
    "Audit the Python tests with unittest and report failed counts."
)
partial=grounding.ground(partial_goal,registry)
assert len(partial["clauses"])==2, partial
assert partial["grounded_clause_count"]>=1, partial
assert partial["broad_objective_decomposition_available"] is False, partial
assert partial["broad_objective_decomposition"] is None, partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, partial

single=grounding.ground(
    "Compare annual launch counts in the recent five-year period with the preceding five-year period",
    {},
)
assert single["broad_objective_decomposition_available"] is True, single

print("INDEPENDENT_PR474_BROAD_MULTICLAUSE_ROUTING_PASS")
