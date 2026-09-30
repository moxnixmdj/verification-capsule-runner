#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
MISSION_REL="canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL="canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
INTENT_REL="canonical/action_intents/2026-09-30_PARENT_THERMOPHYSICS_FAITHFUL_RUNTIME_TASK_A_002.json"
MISSION_ID="PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
RESULT_REL="canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
REPORT=ROOT/"thermophysics-parent-faithful-terminal.json"
BRAIN_MAIN="86dae95f0b0a872df005dd35ea0110cd3914536f"
BRAIN_PR=374
EXPECTED_BLOBS={
  MISSION_REL:"982b883b353b937d8500bd9b70c1929c33313393",
  TASK_REL:"dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
  INTENT_REL:"9d86ae7e9678d9a860039b865a3af4052d1099f9",
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
}

def blob(rel):
    p=subprocess.run(["git","rev-parse","HEAD:"+rel],cwd=ROOT,text=True,capture_output=True)
    return p.stdout.strip().lower() if p.returncode==0 else None

def read_text(path,limit=16000):
    try: return path.read_text(encoding="utf-8",errors="replace")[:limit]
    except Exception: return ""

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False),flush=True)

closure={k:{"expected":v,"observed":blob(k)} for k,v in EXPECTED_BLOBS.items()}
for v in closure.values(): v["match"]=v["expected"]==v["observed"]
if not all(v["match"] for v in closure.values()):
    emit({"schema":"PROJECT_BRAIN_PARENT_THERMOPHYSICS_TERMINAL_V1","status":"CARRIER_CLOSURE_FAIL",
          "brain_main":BRAIN_MAIN,"brain_pr":BRAIN_PR,"mission_id":MISSION_ID,
          "execution_count":0,"task_executed":False,"closure":closure})
    raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    emit({"schema":"PROJECT_BRAIN_PARENT_THERMOPHYSICS_TERMINAL_V1","status":"MODEL_PLANNER_DISABLE_ENV_REQUIRED",
          "execution_count":0,"task_executed":False})
    raise SystemExit(1)

mission=json.loads((ROOT/MISSION_REL).read_text(encoding="utf-8"))
task=json.loads((ROOT/TASK_REL).read_text(encoding="utf-8"))
if mission.get("mission_id")!=MISSION_ID or task.get("task_id")!=MISSION_ID:
    raise SystemExit("MISSION_TASK_ID_MISMATCH")
if (task.get("execution_constraints") or {}).get("exactly_one_execution") is not True:
    raise SystemExit("EXACTLY_ONE_EXECUTION_CONTRACT_MISSING")

env=os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"]="1"
proc=subprocess.run(
    [sys.executable,"canonical/runtime/astra_runtime.py",MISSION_REL],
    cwd=ROOT,text=True,capture_output=True,timeout=1200,env=env
)

state_path=ROOT/"canonical/astra_runtime/state"/(MISSION_ID+".json")
result_path=ROOT/RESULT_REL
evidence_dir=ROOT/"canonical/astra_runtime/evidence"
evidence=[]
if evidence_dir.is_dir():
    for p in sorted(evidence_dir.glob(MISSION_ID+"*")):
        if p.is_file():
            evidence.append({"path":p.relative_to(ROOT).as_posix(),"excerpt":read_text(p,12000)})

result_obj=None
if result_path.is_file():
    try: result_obj=json.loads(result_path.read_text(encoding="utf-8"))
    except Exception: result_obj={"_raw_excerpt":read_text(result_path)}

success=(proc.returncode==0 and result_path.is_file())
report={
  "schema":"PROJECT_BRAIN_PARENT_THERMOPHYSICS_TERMINAL_V1",
  "status":"PRODUCER_SUCCESS_PENDING_INDEPENDENT_ORACLE" if success else "FAIL_FIRST_CAUSAL_GAP",
  "brain_main":BRAIN_MAIN,
  "brain_pr":BRAIN_PR,
  "mission_id":MISSION_ID,
  "mission_path":MISSION_REL,
  "required_entrypoint":"canonical/runtime/astra_runtime.py <canonical mission path>",
  "canonical_entrypoint_invoked":True,
  "direct_goal_compiler_harness_used":False,
  "task_executed":True,
  "execution_count":1,
  "runtime_returncode":proc.returncode,
  "model_planner_disabled":True,
  "incremental_spend_usd":0,
  "closure":closure,
  "stdout_excerpt":proc.stdout[-16000:],
  "stderr_excerpt":proc.stderr[-16000:],
  "state_excerpt":read_text(state_path,16000) if state_path.is_file() else None,
  "evidence":evidence,
  "result_path":RESULT_REL if result_path.is_file() else None,
  "result":result_obj,
  "independent_oracle_executed":False,
  "parent_capability_credit_authorized":False
}
emit(report)
raise SystemExit(0 if success else 2)
