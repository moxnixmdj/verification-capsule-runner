#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import pathlib
import sys
import traceback

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_PATH=ROOT/"canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_20260930_001.json"
REPORT=ROOT/"pr317-open-ended-climate-taskb-report.json"

EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"a73410e38d4c67d92188e934e0c0c3f0b2b329ee",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_20260930_001.json":"61d7334c1c866027260025d0d147d16ee9e0cb02",
}
BRAIN_BASE="0292dc91d7b2354beede3e530256054330fb94d8"
BRAIN_PR=317
TASK_ID="PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-20260930-001"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_PR317_OPEN_ENDED_CLIMATE_TERMINAL_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "path":rel,"expected_blob":expected,"observed_blob":observed,
          "brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,"task_executed":False,
        })
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")

spec=importlib.util.spec_from_file_location("pr317_astra_runtime",RUNTIME/"astra_runtime.py")
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

report={
  "schema":"PROJECT_BRAIN_PR317_OPEN_ENDED_CLIMATE_TERMINAL_V1",
  "status":"STARTED",
  "brain_pr":BRAIN_PR,
  "brain_base":BRAIN_BASE,
  "task_id":TASK_ID,
  "domain":task.get("domain"),
  "task_blob":EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],
  "runtime_blobs":{k:v for k,v in EXPECTED_BLOBS.items() if k!=str(TASK_PATH.relative_to(ROOT))},
  "source_task_replay":False,
  "execution_count":1,
  "incremental_spend_usd":0,
  "model_planner_disabled":True,
}

mission={"mission_id":TASK_ID,"goal":task["goal_text"]}
step={
  "id":"parent_task_b_open_climate",
  "adapter":"goal",
  "goal_ref":"goal",
  "verified_initial_facts":["network.http.available"],
  "max_controller_actions":32,
  "allow_optional_model_planner":False,
}

try:
    result=runtime.execute_step(step,[],mission)
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":type(exc).__name__+":"+str(exc),
      "independent_oracle_executed":False,
      "traceback_tail":traceback.format_exc()[-6000:],
    })
    emit(report)
    raise SystemExit(2)

report["runtime_result"]=result
report["runtime_provenance"]={
  "model_dependency_count":result.get("model_dependency_count"),
  "cognition_dependency_class":result.get("cognition_dependency_class"),
  "cognition_provenance_authority":result.get("cognition_provenance_authority"),
  "controller_mode":result.get("controller_mode"),
  "planner_model_last":result.get("planner_model_last"),
}
if result.get("model_dependency_count")!=0:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"RUNTIME_DERIVED_MODEL_DEPENDENCY_NONZERO",
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(3)
if result.get("cognition_provenance_authority")!="ASTRA_RUNTIME_DERIVED_V1":
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"RUNTIME_COGNITION_PROVENANCE_MISSING",
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(4)
if str(result.get("controller_mode") or "").startswith("OPTIONAL_MODEL_ADVISORY") or result.get("planner_model_last") not in (None,""):
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"MODEL_CONTROLLER_PRESENT",
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(5)

required=task["required_output"]
output_path=ROOT/required["output_path"]
if not output_path.is_file():
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_DECISION_QUALITY_RESULT_NOT_MATERIALIZED",
      "required_output_path":required["output_path"],
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(6)

try:
    output=json.loads(output_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OUTPUT_INVALID_JSON:"+type(exc).__name__,
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(7)

missing=[k for k in required["fields"] if k not in output]
if missing:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "task_executed":True,
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OUTPUT_FIELDS_MISSING:"+",".join(missing),
      "producer_output":output,
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(8)

report.update({
  "status":"PRODUCER_PASS_PENDING_INDEPENDENT_ORACLE",
  "task_executed":True,
  "parent_task_completed":False,
  "producer_output_path":required["output_path"],
  "producer_output_sha256":hashlib.sha256(output_path.read_bytes()).hexdigest(),
  "producer_output":output,
  "independent_oracle_executed":False,
})
emit(report)
