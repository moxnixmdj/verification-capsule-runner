#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_PATH=ROOT/"canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT=ROOT/"pr337-parent-climate-open-taska-producer-report.json"
BRAIN_BASE="797d5fbea5f230a31044006755beb98ae387134b"
BRAIN_PR=337
BRAIN_HEAD="0af30865752f71da09af7b324ab1ab734855290f"
TASK_ID="PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"
EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py": "443e3386f11156e55635556b6e8f8ad7d7733592",
  "canonical/runtime/bound_capabilities/jq_query.py": "f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/capability_proposal_generators.py": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py": "64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py": "6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json": "6f0e889e23cfba6c511b3a54cb86acba48bc9d3a"
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True,default=str),flush=True)

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_PRODUCER_TERMINAL_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "path":rel,"expected_blob":expected,"observed_blob":observed,
          "brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,"brain_head":BRAIN_HEAD,
          "task_executed":False,"execution_count":0
        })
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    raise SystemExit("MODEL_PLANNER_DISABLE_ENV_REQUIRED")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("pr337_astra_runtime",RUNTIME/"astra_runtime.py")
goal=str(task.get("goal_text") or "").strip()
if not goal:
    raise SystemExit("GOAL_TEXT_MISSING")

report={
  "schema":"PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_PRODUCER_TERMINAL_V1",
  "status":"STARTED",
  "brain_pr":BRAIN_PR,
  "brain_base":BRAIN_BASE,
  "brain_head":BRAIN_HEAD,
  "task_id":TASK_ID,
  "domain":task.get("domain"),
  "task_blob":EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],
  "runtime_blobs":{k:v for k,v in EXPECTED_BLOBS.items() if k!=str(TASK_PATH.relative_to(ROOT))},
  "source_task_replay":False,
  "execution_count":1,
  "model_planner_disabled":True,
  "incremental_spend_usd":0
}
step={
  "id":"parent_climate_open_taska",
  "goal_ref":"goal",
  "max_controller_actions":32,
  "max_cycles":6,
  "allow_optional_model_planner":False
}
mission={"mission_id":TASK_ID,"goal":goal}
try:
    result=runtime.run_goal(step,mission)
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":type(exc).__name__+":"+str(exc),
      "independent_oracle_executed":False
    })
    emit(report)
    raise SystemExit(2)

if not isinstance(result,dict):
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"GOAL_RESULT_NOT_OBJECT",
      "independent_oracle_executed":False
    })
    emit(report)
    raise SystemExit(3)

prov_fail=[]
if result.get("model_dependency_count")!=0:
    prov_fail.append("MODEL_DEPENDENCY_COUNT_NONZERO")
if result.get("cognition_provenance_authority")!="ASTRA_RUNTIME_DERIVED_V1":
    prov_fail.append("RUNTIME_PROVENANCE_AUTHORITY_MISSING")
if str(result.get("controller_mode") or "").startswith("OPTIONAL_MODEL_ADVISORY"):
    prov_fail.append("MODEL_ADVISORY_CONTROLLER_PRESENT")
if result.get("planner_model_last") not in (None,""):
    prov_fail.append("PLANNER_MODEL_PRESENT")
if prov_fail:
    report.update({
      "status":"FAIL_PROVENANCE",
      "task_executed":True,
      "parent_task_completed":False,
      "runtime_result":result,
      "provenance_failures":prov_fail,
      "independent_oracle_executed":False
    })
    emit(report)
    raise SystemExit(4)

report.update({
  "status":"PRODUCER_SUCCESS_PENDING_INDEPENDENT_VERIFICATION",
  "task_executed":True,
  "parent_task_completed":True,
  "runtime_result":result,
  "runtime_derived_model_dependency_count":result.get("model_dependency_count"),
  "cognition_provenance_authority":result.get("cognition_provenance_authority"),
  "independent_oracle_executed":False
})
emit(report)
