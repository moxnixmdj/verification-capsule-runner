#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
BOUND=RUNTIME/"bound_capabilities"
REPORT=ROOT/"broad-routing-independent-report.json"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

dec=load(BOUND/"broad_objective_decompose.py","qual_broad_decomp")
ground=load(BOUND/"plain_goal_bound_grounding.py","qual_grounding")
runtime=load(RUNTIME/"astra_runtime.py","qual_runtime")

objectives=[
    (
      "Assess whether the maximum rated operating temperature is greater than the default "
      "recommended operating temperature. Use authoritative primary technical evidence and "
      "a real executable check. Autonomously discover and verify the relevant documentation, "
      "choose and run a zero-cost verification method, identify material limitations, "
      "independently verify the consequential result, and produce a decision-quality answer "
      "with provenance."
    ),
    (
      "Determine whether the maximum permitted queue depth is greater than the default queue "
      "depth. Use authoritative primary technical evidence and a real executable check. "
      "Autonomously discover and verify the relevant documentation, determine how to extract "
      "and interpret the required limits, choose and run a zero-cost verification method, "
      "identify material scope limitations, independently verify the consequential result, "
      "and produce a decision-quality answer with provenance."
    ),
]
checks=[]

for i,goal in enumerate(objectives):
    d=dec.decompose(goal)
    assert d["status"]=="DECOMPOSED",d
    assert d["model_dependency_count"]==0,d
    g=ground.ground(goal,{})
    assert len(g["clauses"])>1,g
    assert g["grounded_clause_count"]==0,g
    assert g["unresolved_clause_indexes"]==list(range(len(g["clauses"]))),g
    assert g["broad_objective_decomposition_available"] is True,g
    assert g["broad_objective_decomposition"]["status"]=="DECOMPOSED",g
    checks.append({"case":f"cross_domain_{i}","status":"PASS","clause_count":len(g["clauses"])})

generic=(
  "Assess whether a material property differs between two operating regimes. "
  "Use authoritative primary technical evidence and a real executable check. "
  "Autonomously discover and verify relevant sources, choose and run a zero-cost "
  "verification method, identify material scope limitations, independently verify "
  "the consequential result, and produce a decision-quality answer."
)
gd=dec.decompose(generic)
assert gd["status"]=="DECOMPOSED",gd
checks.append({"case":"generic_method_language_not_recipe","status":"PASS"})

for recipe in (
    "Assess whether two measured values differ. Run python verify_values.py",
    "Assess whether values differ using https://example.com/data and extract JSON path value",
    "Assess whether values differ. Execute ./verify_values.sh",
):
    out=dec.decompose(recipe)
    assert out["status"]=="UNSUPPORTED",out
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",out
checks.append({"case":"concrete_recipes_fail_closed","status":"PASS","count":3})

registry={
  "material.temperature.assess":{
    "status":"VERIFIED_BOUND_CAPABILITY",
    "incremental_spend_usd":0,
    "provides":["material.temperature.assessment"],
    "requires":[],
    "keywords":["assess","material","temperature","rated","operating"],
  }
}
partial_goal=(
  "Assess material operating temperature using the verified local assessment. "
  "Autonomously discover authoritative evidence for a separate unresolved claim."
)
partial=ground.ground(partial_goal,registry)
assert partial["grounded_clause_count"]>=1,partial
assert partial["broad_objective_decomposition_available"] is False,partial
assert partial["broad_objective_decomposition"] is None,partial
checks.append({"case":"partial_grounding_blocks_whole_goal_decomposition","status":"PASS"})

routing_goal=objectives[0]
routing_ground=ground.ground(routing_goal,{})
mission={"mission_id":"INDEPENDENT-BROAD-RESEARCH-ROUTING-QUALIFICATION","goal":routing_goal}
step={"adapter":"goal","goal_ref":"goal","allow_optional_model_planner":False}
compile_error=runtime.Blocker(
    "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
)
frontend={
  "status":"SOURCE_DISCOVERY_BLOCKED",
  "provenance_verified_candidate_count":0,
  "authority_identity_verified_candidate_count":0,
  "relevance_verified_candidate_count":0,
  "claim_relation_evaluated_count":0,
  "next_required_capability":"MODEL_INDEPENDENT_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1",
}
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td)
    grounding_path=td/"grounding.json"
    frontend_path=td/"frontend.json"
    acquisition_loaded={"value":False}
    def forbidden_acquisition():
        acquisition_loaded["value"]=True
        raise AssertionError("PACKAGE_ACQUISITION_REACHED_FOR_BROAD_RESEARCH")
    with mock.patch.object(runtime,"EVID_DIR",td), \
         mock.patch.object(runtime,"_compile_plain_goal",side_effect=compile_error), \
         mock.patch.object(
             runtime,
             "_ground_plain_goal_to_bound_capabilities",
             return_value=(grounding_path,routing_ground),
         ), \
         mock.patch.object(
             runtime,
             "_run_open_research_source_frontend",
             return_value=(frontend_path,frontend),
         ) as frontend_call, \
         mock.patch.object(
             runtime,
             "_load_auto_capability_acquisition",
             side_effect=forbidden_acquisition,
         ):
        try:
            runtime.run_goal(step,mission)
        except runtime.Blocker as exc:
            text=str(exc)
            assert "OPEN_ENDED_RESEARCH_SOURCE_FRONTEND_BLOCKED" in text,text
        else:
            raise AssertionError("EXPECTED_SOURCE_FRONTEND_BLOCKER")
        assert frontend_call.call_count==1,frontend_call.call_count
        assert acquisition_loaded["value"] is False
checks.append({"case":"runtime_research_frontend_precedes_package_acquisition","status":"PASS"})

report={
  "schema":"PROJECT_BRAIN_BROAD_RESEARCH_ROUTING_INDEPENDENT_QUALIFICATION_V1",
  "status":"PASS",
  "candidate":{
    "brain_pr":474,
    "brain_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
    "broad_objective_decompose_blob":blob(BOUND/"broad_objective_decompose.py"),
    "plain_goal_bound_grounding_blob":blob(BOUND/"plain_goal_bound_grounding.py"),
    "astra_runtime_blob":blob(RUNTIME/"astra_runtime.py"),
  },
  "checks":checks,
  "check_count":len(checks),
  "package_acquisition_reached":False,
  "parent_task_executed":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
