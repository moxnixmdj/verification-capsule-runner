#!/usr/bin/env python3
import hashlib, importlib.util, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED_GROUNDING_BLOB="25738e959dec0be46058e4bd7720fb8ed1b599bb"
EXPECTED_BROAD_BLOB="6eb2b20e860da466ad8b793c20060ded1fbf389b"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name, filename):
    p=ROOT/filename
    spec=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

gp=ROOT/"plain_goal_bound_grounding.py"
bp=ROOT/"broad_objective_decompose.py"
assert git_blob_sha(gp)==EXPECTED_GROUNDING_BLOB, (git_blob_sha(gp),EXPECTED_GROUNDING_BLOB)
assert git_blob_sha(bp)==EXPECTED_BROAD_BLOB, (git_blob_sha(bp),EXPECTED_BROAD_BLOB)
g=load("pr468_grounding","plain_goal_bound_grounding.py")

goal=("Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than the protocol's default initial stream flow-control window. "
      "Use authoritative primary technical evidence and a real executable check. "
      "Autonomously discover and verify the relevant specification, determine how to extract and interpret the required limits, choose and run a zero-cost verification method, identify material protocol-scope or interpretation limitations, independently verify the consequential result, and produce a decision-quality answer with provenance.")

out=g.ground(goal,{})
assert len(out["clauses"])>1, out
assert out["grounded_clause_count"]==0, out
assert len(out["unresolved_clause_indexes"])==len(out["clauses"]), out
assert out["broad_objective_decomposition_available"] is True, out
broad=out["broad_objective_decomposition"]
assert broad and broad["status"]=="DECOMPOSED", out
assert broad["model_dependency_count"]==0, broad
assert [r["role"] for r in broad["roles"]]==[
    "SOURCE_DISCOVERY","EVIDENCE_ACQUISITION","EVIDENCE_EXTRACTION",
    "RELATION_EVALUATION","DECISION_SYNTHESIS_AND_VERIFICATION"
], broad

unsupported=g.ground("Create output.json with one record",{})
assert unsupported["broad_objective_decomposition_available"] is False, unsupported

partial_registry={
  "HTTP2_FLOW_CONTROL_BOUND":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["http2 flow control initial stream window"],
    "requires":[],
    "keywords":["http2 flow control stream window protocol"],
    "source":{"type":"independent_qualification_fixture"}
  }
}
partial=g.ground(goal,partial_registry)
assert partial["grounded_clause_count"]>0, partial
assert partial["broad_objective_decomposition_available"] is False, partial
assert partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True, partial

print("PR468_INDEPENDENT_QUALIFICATION_PASS")
print("exact_candidate_blob="+EXPECTED_GROUNDING_BLOB)
print("exact_dependency_blob="+EXPECTED_BROAD_BLOB)
print("http2_clause_count="+str(len(out["clauses"])))
print("partial_grounded_clause_count="+str(partial["grounded_clause_count"]))
