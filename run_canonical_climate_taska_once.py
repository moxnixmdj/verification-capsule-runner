#!/usr/bin/env python3
import hashlib, json, os, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_PATH=ROOT/"canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT=ROOT/"canonical-climate-taska-terminal.json"
EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json":"6f0e889e23cfba6c511b3a54cb86acba48bc9d3a"
}
BRAIN_BASE="ca16a72e8e83f5274b04265fe02eb7729451da93"
TASK_ID="PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True))

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({"schema":"PROJECT_BRAIN_PARENT_OPENENDED_CLIMATE_TASK_A_TERMINAL_V1",
              "status":"CARRIER_CLOSURE_FAIL","task_executed":False,
              "brain_base":BRAIN_BASE,"path":rel,
              "expected_blob":expected,"observed_blob":observed})
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
constraints=task.get("execution_constraints") or {}
anti=task.get("anti_leakage") or {}
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")
if any(v is not False for v in anti.values()):
    raise SystemExit("TASK_ANTI_LEAKAGE_CONTRACT_INVALID")
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    raise SystemExit("MODEL_PLANNER_DISABLE_ENV_MISSING")

sys.path.insert(0,str(ROOT))
from canonical.runtime import astra_runtime

report={
  "schema":"PROJECT_BRAIN_PARENT_OPENENDED_CLIMATE_TASK_A_TERMINAL_V1",
  "status":"STARTED","brain_base":BRAIN_BASE,"task_id":TASK_ID,
  "task_blob":EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],
  "runtime_blob":EXPECTED_BLOBS["canonical/runtime/astra_runtime.py"],
  "execution_count":1,"task_executed":True,"source_task_replay":False,
  "model_planner_disabled":True,"incremental_spend_usd":0,
  "prewired_authority":False,"prewired_source_url":False,
  "prewired_formula":False,"prewired_controller_action_graph":False
}
mission={"mission_id":TASK_ID,"goal":str(task["goal_text"])}
step={"id":"canonical_openended_climate_taska","goal_ref":"goal",
      "allow_optional_model_planner":False,"max_controller_actions":32}
try:
    run=astra_runtime.run_goal(step,mission)
except Exception as exc:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"EXECUTE:"+type(exc).__name__+":"+str(exc),
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(2)

report["runtime_result"]=run
if run.get("model_dependency_count")!=0:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"RUNTIME_MODEL_DEPENDENCY_NONZERO",
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(3)
if run.get("cognition_provenance_authority")!="ASTRA_RUNTIME_DERIVED_V1":
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"RUNTIME_COGNITION_PROVENANCE_AUTHORITY_INVALID",
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(4)
if run.get("controller_mode")!="MODEL_INDEPENDENT_ACTION_PLAN":
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"RUNTIME_CONTROLLER_MODE_INELIGIBLE",
                   "observed_controller_mode":run.get("controller_mode"),
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(5)
if any(run.get(k) not in (None,"") for k in ("planner_source","planner_transport","planner_model_last")):
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"RUNTIME_PLANNER_MARKER_PRESENT",
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(6)

out_path=ROOT/str((task.get("required_output") or {}).get("output_path") or "")
if not out_path.is_file():
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"REQUIRED_OUTPUT_ARTIFACT_MISSING",
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(7)
try:
    producer=json.loads(out_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"REQUIRED_OUTPUT_INVALID_JSON:"+type(exc).__name__,
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(8)
required=list((task.get("required_output") or {}).get("fields") or [])
missing=[k for k in required if k not in producer]
if missing:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"REQUIRED_OUTPUT_FIELDS_MISSING",
                   "missing_fields":missing,"producer_result":producer,
                   "independent_oracle_executed":False})
    emit(report); raise SystemExit(9)
if producer.get("model_dependency_count")!=0:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
                   "first_causal_blocker":"PRODUCER_MODEL_DEPENDENCY_NONZERO",
                   "producer_result":producer,"independent_oracle_executed":False})
    emit(report); raise SystemExit(10)
report.update({"status":"PRODUCER_PASS_PENDING_INDEPENDENT_ORACLE",
               "parent_task_completed":True,"producer_result":producer,
               "independent_oracle_executed":False})
emit(report)
