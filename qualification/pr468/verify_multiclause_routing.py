#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
REPORT=ROOT/"pr468-independent-report.json"
EXPECTED_GROUNDING_BLOB="46e8e7466479ea298c34e5fa682d49c374510ce9"
EXPECTED_BROAD_BLOB="1efaec4ba51ecb5c40072b3190853f4de89d8f77"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name,filename):
    p=ROOT/filename
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+filename)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

gp=ROOT/"plain_goal_bound_grounding.py"
bp=ROOT/"broad_objective_decompose.py"
observed_grounding=git_blob_sha(gp)
observed_broad=git_blob_sha(bp)
assert observed_grounding==EXPECTED_GROUNDING_BLOB,(observed_grounding,EXPECTED_GROUNDING_BLOB)
assert observed_broad==EXPECTED_BROAD_BLOB,(observed_broad,EXPECTED_BROAD_BLOB)

g=load("pr470_grounding","plain_goal_bound_grounding.py")
d=load("pr470_decomposer","broad_objective_decompose.py")
checks=[]

def ok(name,condition,detail=None):
    assert condition,(name,detail)
    checks.append({"name":name,"status":"PASS","detail":detail})

http2=("Assess whether the maximum permitted HTTP/2 initial stream flow-control window is greater than the protocol's default initial stream flow-control window. "
       "Use authoritative primary technical evidence and a real executable check. "
       "Autonomously discover and verify the relevant specification, determine how to extract and interpret the required limits, choose and run a zero-cost verification method, identify material protocol-scope or interpretation limitations, independently verify the consequential result, and produce a decision-quality answer with provenance.")
out=g.ground(http2,{})
ok("spent_http2_shape_reaches_broad_decomposition",
   len(out["clauses"])>1 and out["grounded_clause_count"]==0
   and len(out["unresolved_clause_indexes"])==len(out["clauses"])
   and out["broad_objective_decomposition_available"] is True
   and out["broad_objective_decomposition"]["status"]=="DECOMPOSED",
   {"clauses":len(out["clauses"]),"roles":[r["role"] for r in out["broad_objective_decomposition"]["roles"]]})

fresh=("Evaluate whether a material fatigue threshold differs between two operating regimes. "
       "Use authoritative primary technical evidence and a real executable check. "
       "Autonomously discover and verify relevant sources, choose and run a zero-cost verification method, "
       "identify material scope limitations, independently verify the consequential result, and produce a decision-quality answer.")
fresh_direct=d.decompose(fresh)
fresh_ground=g.ground(fresh,{})
ok("fresh_cross_domain_generic_run_language_admitted",
   fresh_direct["status"]=="DECOMPOSED"
   and fresh_ground["broad_objective_decomposition_available"] is True,
   {"direct_status":fresh_direct["status"],"clauses":len(fresh_ground["clauses"])})

explicit="Assess whether two measured values differ. Run python verify_values.py"
exp=d.decompose(explicit)
ok("concrete_execution_recipe_still_rejected",
   exp["status"]=="UNSUPPORTED" and exp["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",
   {"reason":exp.get("reason")})

generic_method=(
    "Assess whether a thermal property differs between two operating regimes. "
    "Use authoritative primary technical evidence and a real executable check. "
    "Autonomously discover and verify relevant sources, choose and run a zero-cost "
    "verification method, identify material scope limitations, independently verify "
    "the consequential result, and produce a decision-quality answer."
)
generic_out=d.decompose(generic_method)
assert generic_out["status"]=="DECOMPOSED", generic_out

concrete_out=d.decompose("Assess whether two measured values differ. Run python verify_values.py")
assert concrete_out["status"]=="UNSUPPORTED", concrete_out
assert concrete_out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", concrete_out

url_out=d.decompose("Assess whether two measured values differ using https://example.com/data")
assert url_out["status"]=="UNSUPPORTED", url_out
assert url_out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE", url_out
print("PR474_EXPLICIT_RECIPE_BOUNDARY_PASS")

unsupported=g.ground("Create output.json with one record",{})
ok("nonresearch_action_not_reinterpreted",
   unsupported["broad_objective_decomposition_available"] is False
   and unsupported["broad_objective_decomposition"] is None)

single=g.ground("Compare annual launch counts in the recent five-year period with the preceding five-year period",{})
ok("single_clause_prior_behavior_preserved",
   single["grounded_clause_count"]==0
   and single["unresolved_clause_indexes"]==[0]
   and single["broad_objective_decomposition_available"] is True)

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
partial=g.ground(http2,partial_registry)
ok("partial_grounding_does_not_escape_to_whole_goal_broad_route",
   partial["grounded_clause_count"]>0
   and partial["broad_objective_decomposition_available"] is False
   and partial["whole_goal_external_discovery_forbidden_if_any_bound_grounding"] is True,
   {"grounded_clause_count":partial["grounded_clause_count"]})

report={
 "schema":"PROJECT_BRAIN_PR474_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":474,
 "brain_pr_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
 "candidate_blobs":{"broad_objective_decompose.py":observed_broad,"plain_goal_bound_grounding.py":observed_grounding},
 "checks":checks,
 "model_dependency_count":0,
 "parent_task_execution_count":0,
 "incremental_spend_usd":0
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
