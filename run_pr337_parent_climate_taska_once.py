#!/usr/bin/env python3
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_PATH=ROOT/"canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT=ROOT/"pr337-parent-climate-taska-terminal.json"

BRAIN_BASE="797d5fbea5f230a31044006755beb98ae387134b"
BRAIN_PR=337
BRAIN_HEAD_AT_CAPSULE_INSTALL="aa1f60088b645439ff1eb15284dee828cb6b0671"
TASK_ID="PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"

EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py":"443e3386f11156e55635556b6e8f8ad7d7733592",
  "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json":"6f0e889e23cfba6c511b3a54cb86acba48bc9d3a",
}

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True,default=str))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

# Closure must pass before the scarce producer execution is counted.
for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "task_executed":False,
          "execution_count":0,
          "brain_pr":BRAIN_PR,
          "brain_base":BRAIN_BASE,
          "brain_head_at_capsule_install":BRAIN_HEAD_AT_CAPSULE_INSTALL,
          "path":rel,
          "expected_blob":expected,
          "observed_blob":observed,
          "observed_at_utc":utc(),
        })
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    emit({
      "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
      "status":"MODEL_PLANNER_DISABLEMENT_NOT_PROVEN",
      "task_executed":False,
      "execution_count":0,
      "brain_pr":BRAIN_PR,
      "brain_base":BRAIN_BASE,
      "observed_at_utc":utc(),
    })
    raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
constraints=task.get("execution_constraints") or {}
required={
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "no_frontier_model_cognition":True,
  "no_local_model":True,
  "no_model_artifact":True,
  "no_task_specific_runtime_patch":True,
  "exactly_one_execution":True,
  "stop_on_first_causal_gap":True,
}
for key,value in required.items():
    if constraints.get(key)!=value:
        raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID:"+key)

runtime=load("pr337_astra_runtime",RUNTIME/"astra_runtime.py")
mission={
  "mission_id":TASK_ID,
  "goal":str(task["goal_text"]),
  "_runtime_mission_path":str(TASK_PATH.relative_to(ROOT)),
}
step={
  "id":"parent_openended_climate_task_a",
  "adapter":"goal",
  "goal_ref":"goal",
  "allow_optional_model_planner":False,
  "max_cycles":6,
}
report={
  "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
  "status":"STARTED",
  "brain_pr":BRAIN_PR,
  "brain_base":BRAIN_BASE,
  "brain_head_at_capsule_install":BRAIN_HEAD_AT_CAPSULE_INSTALL,
  "task_id":TASK_ID,
  "task_blob":EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],
  "runtime_blobs":{k:v for k,v in EXPECTED_BLOBS.items() if k!=str(TASK_PATH.relative_to(ROOT))},
  "task_executed":True,
  "execution_count":1,
  "model_planner_disabled":True,
  "incremental_spend_usd":0,
  "producer_started_at_utc":utc(),
}
try:
    result=runtime.run_goal(step,mission)
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"RUN_GOAL:"+type(exc).__name__+":"+str(exc),
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(2)

if not isinstance(result,dict):
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"RUN_GOAL_RESULT_NOT_OBJECT",
      "runtime_result_type":type(result).__name__,
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(3)

report["runtime_result"]=result
provenance_failures=[]
if result.get("cognition_provenance_authority")!="ASTRA_RUNTIME_DERIVED_V1":
    provenance_failures.append("COGNITION_PROVENANCE_AUTHORITY_INVALID")
if result.get("model_dependency_count")!=0:
    provenance_failures.append("MODEL_DEPENDENCY_COUNT_NONZERO")
if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":
    provenance_failures.append("COGNITION_DEPENDENCY_CLASS_NOT_MODEL_INDEPENDENT")
if str(result.get("controller_mode") or "")!="MODEL_INDEPENDENT_ACTION_PLAN":
    provenance_failures.append("CONTROLLER_MODE_NOT_MODEL_INDEPENDENT_ACTION_PLAN")
if result.get("planner_source") not in (None,""):
    provenance_failures.append("PLANNER_SOURCE_PRESENT")
if result.get("planner_transport") not in (None,""):
    provenance_failures.append("PLANNER_TRANSPORT_PRESENT")
if result.get("planner_model_last") not in (None,""):
    provenance_failures.append("PLANNER_MODEL_PRESENT")
if provenance_failures:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"RUNTIME_COGNITION_PROVENANCE_INVALID:"+",".join(provenance_failures),
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(4)

output_rel=str((task.get("required_output") or {}).get("output_path") or "").strip()
output_path=ROOT/output_rel if output_rel else None
if output_path is None or not output_path.is_file():
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OUTPUT_MISSING_AFTER_RUN_GOAL",
      "required_output_path":output_rel,
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(5)

try:
    producer=json.loads(output_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OUTPUT_INVALID_JSON:"+type(exc).__name__+":"+str(exc),
      "required_output_path":output_rel,
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(6)

missing=[f for f in ((task.get("required_output") or {}).get("fields") or []) if f not in producer]
if missing:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OUTPUT_FIELDS_MISSING:"+",".join(missing),
      "required_output_path":output_rel,
      "producer_output":producer,
      "independent_oracle_executed":False,
      "producer_completed_at_utc":utc(),
    })
    emit(report)
    raise SystemExit(7)

report.update({
  "status":"PRODUCER_SUCCESS_PENDING_INDEPENDENT_ORACLE",
  "parent_task_completed":False,
  "producer_output":producer,
  "required_output_path":output_rel,
  "independent_oracle_executed":False,
  "producer_completed_at_utc":utc(),
})
emit(report)
