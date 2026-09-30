#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_REL="canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
RUNTIME_REL="canonical/runtime/astra_runtime.py"
REPORT=ROOT/"thermophysics-parent-terminal.json"
EXPECTED={
  RUNTIME_REL:"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
}

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True))

task=json.loads((ROOT/TASK_REL).read_text(encoding="utf-8"))
mission=json.loads((ROOT/MISSION_REL).read_text(encoding="utf-8"))
task_id=task["task_id"]
report={
  "schema":"PROJECT_BRAIN_FAITHFUL_OPEN_ENDED_PARENT_TERMINAL_V1",
  "task_id":task_id,
  "brain_merge_commit":"fc07395c387563cbb2b3dfdc3b14fd80239a080b",
  "task_executed":False,
  "execution_count":0,
  "source_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "entrypoint":"canonical/runtime/astra_runtime.py <canonical mission path>",
  "direct_goal_compiler_harness_used":False,
}

for rel,expected in EXPECTED.items():
    got=blob(ROOT/rel) if (ROOT/rel).is_file() else None
    if got!=expected:
        report.update(status="CARRIER_CLOSURE_FAIL",path=rel,expected_blob=expected,observed_blob=got)
        emit(report); raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    report.update(status="CARRIER_POLICY_FAIL",first_causal_blocker="MODEL_PLANNER_NOT_DISABLED")
    emit(report); raise SystemExit(1)

if task.get("execution_constraints",{}).get("exactly_one_execution") is not True:
    raise SystemExit("ONE_SHOT_CONTRACT_MISSING")
if task.get("execution_constraints",{}).get("required_execution_entrypoint")!="canonical/runtime/astra_runtime.py <canonical mission path>":
    raise SystemExit("ENTRYPOINT_CONTRACT_MISMATCH")
if mission.get("mission_id")!=task_id:
    raise SystemExit("MISSION_ID_MISMATCH")

report["task_executed"]=True
report["execution_count"]=1
proc=subprocess.run(
  [sys.executable,str(ROOT/RUNTIME_REL),MISSION_REL],
  cwd=ROOT,text=True,capture_output=True,timeout=660,env=os.environ.copy()
)
report["runtime_returncode"]=proc.returncode
report["runtime_stdout_tail"]=proc.stdout[-12000:]
report["runtime_stderr_tail"]=proc.stderr[-12000:]

state_path=ROOT/"canonical/astra_runtime/state"/(task_id+".json")
if state_path.is_file():
    state=json.loads(state_path.read_text(encoding="utf-8"))
    report["runtime_state"]=state
else:
    state=None
    report["runtime_state_missing"]=True

output_rel=task.get("required_output",{}).get("output_path")
output_path=ROOT/str(output_rel or "")
producer=None
if output_rel and output_path.is_file():
    try:
        producer=json.loads(output_path.read_text(encoding="utf-8"))
        report["producer_output"]=producer
    except Exception as exc:
        report["producer_output_parse_error"]=type(exc).__name__+":"+str(exc)

if proc.returncode!=0 or not isinstance(state,dict) or state.get("status")!="COMPLETE":
    blocker=(state or {}).get("blocker") if isinstance(state,dict) else None
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker=blocker or ("RUNTIME_RETURN_CODE_"+str(proc.returncode)),
      replay_allowed=False,
    )
    emit(report); raise SystemExit(2)

if not isinstance(producer,dict):
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="REQUIRED_DECISION_QUALITY_OUTPUT_MISSING_OR_INVALID",
      replay_allowed=False,
    )
    emit(report); raise SystemExit(3)

required=list(task.get("required_output",{}).get("fields") or [])
missing=[x for x in required if x not in producer]
if missing:
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="REQUIRED_OUTPUT_FIELDS_MISSING:"+",".join(missing),
      replay_allowed=False,
    )
    emit(report); raise SystemExit(4)

if producer.get("model_dependency_count")!=0:
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="MODEL_INDEPENDENCE_CONTRACT_FAILED",
      replay_allowed=False,
    )
    emit(report); raise SystemExit(5)

report.update(
  status="PRODUCER_COMPLETED_PENDING_INDEPENDENT_ORACLE",
  parent_task_completed=False,
  producer_semantic_output_present=True,
  independent_oracle_executed=False,
  replay_allowed=False,
  parent_capability_credit_authorized=False,
  next_required_action="INDEPENDENTLY_REFETCH_PRODUCER_CITED_AUTHORITATIVE_SOURCES_AND_RECOMPUTE_DECLARED_METHOD_WITHOUT_IMPORTING_PRODUCER_MODULES",
)
emit(report)
