#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_ID="PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
TASK_REL="canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
RUNTIME_REL="canonical/runtime/astra_runtime.py"
REPORT=ROOT/"openended-sqlite-taska-terminal.json"
BRAIN_MERGE="3ce64b1abb2e6542659617563af48e44eb33f996"
EXPECTED_BLOBS={
    TASK_REL:"5d09c9eebcb09612525836e7926bdf297f4bad32",
    MISSION_REL:"595258cb7b6a4a58053b8bf9bdf87196fad16bd0",
    RUNTIME_REL:"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/python_codec_probe.py":"fc8b5005a9888422e3cb61f6cf0bd147c740ec84",
    "canonical/runtime/verify_pending_cli_binding.py":"a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
    "canonical/runtime/promote_pending_binding.py":"f100c0d1ce5a4b07af0175035c3122d816459b0b",
}

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True,default=str),flush=True)

report={
    "schema":"PROJECT_BRAIN_CANONICAL_OPEN_ENDED_PARENT_TERMINAL_V2",
    "task_id":TASK_ID,
    "brain_merge_commit":BRAIN_MERGE,
    "task_executed":False,
    "execution_count":0,
    "source_task_replay":False,
    "incremental_spend_usd":0,
    "model_planner_disabled":os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")=="1",
    "entrypoint":"canonical/runtime/astra_runtime.py <canonical mission path>",
    "direct_goal_compiler_harness_used":False,
}

closure={}
for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    got=blob(p) if p.is_file() else None
    closure[rel]={"expected":expected,"observed":got,"match":got==expected}
report["closure"]=closure
if not all(x["match"] for x in closure.values()):
    report.update(status="PRESTART_CARRIER_CLOSURE_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(1)

task=json.loads((ROOT/TASK_REL).read_text(encoding="utf-8"))
mission=json.loads((ROOT/MISSION_REL).read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID or mission.get("mission_id")!=TASK_ID:
    report.update(status="PRESTART_IDENTITY_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(2)
if mission.get("goal")!=task.get("goal_text"):
    report.update(status="PRESTART_GOAL_BINDING_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(3)
anti=task.get("anti_leakage") or {}
if any(bool(v) for v in anti.values()):
    report.update(status="PRESTART_ANTI_LEAKAGE_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(4)
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    report.update(status="PRESTART_TASK_CONTRACT_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(5)
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    report.update(status="PRESTART_MODEL_PLANNER_POLICY_FAIL",replay_allowed=True,replay_reason="NO_PRODUCER_EXECUTION")
    emit(report); raise SystemExit(6)

report["task_executed"]=True
report["execution_count"]=1
proc=subprocess.run(
    [sys.executable,str(ROOT/RUNTIME_REL),MISSION_REL],
    cwd=ROOT,text=True,capture_output=True,timeout=660,
    env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"},
)
report["runtime_returncode"]=proc.returncode
report["runtime_stdout_tail"]=proc.stdout[-16000:]
report["runtime_stderr_tail"]=proc.stderr[-16000:]

state_path=ROOT/"canonical/astra_runtime/state"/(TASK_ID+".json")
state=None
if state_path.is_file():
    state=json.loads(state_path.read_text(encoding="utf-8"))
    report["runtime_state"]=state
else:
    report["runtime_state_missing"]=True

if proc.returncode!=0 or not isinstance(state,dict) or state.get("status")!="COMPLETE":
    blocker=state.get("blocker") if isinstance(state,dict) else None
    report.update(
        status="FAIL_FIRST_CAUSAL_GAP",
        parent_task_completed=False,
        independent_oracle_executed=False,
        first_causal_blocker=blocker or ("RUNTIME_RETURN_CODE_"+str(proc.returncode)),
        replay_allowed=False,
        parent_capability_credit_authorized=False,
    )
    emit(report); raise SystemExit(7)

history=state.get("history") or []
producer=(history[-1].get("result") if history and isinstance(history[-1],dict) else None)
report["producer_result"]=producer
prov_ok=(
    isinstance(producer,dict)
    and producer.get("model_dependency_count")==0
    and producer.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
    and producer.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
)
if not prov_ok:
    report.update(
        status="FAIL_COGNITION_PROVENANCE",
        parent_task_completed=False,
        independent_oracle_executed=False,
        replay_allowed=False,
        parent_capability_credit_authorized=False,
    )
    emit(report); raise SystemExit(8)

report.update(
    status="PRODUCER_COMPLETED_PENDING_INDEPENDENT_ORACLE",
    parent_task_completed=False,
    independent_oracle_executed=False,
    replay_allowed=False,
    parent_capability_credit_authorized=False,
    next_required_action="INDEPENDENTLY_INSPECT_PRODUCER_EVIDENCE_AND_REPRODUCE_THE_ESSENTIAL_SQLITE_CONCURRENCY_BACKUP_EXPERIMENT_WITHOUT_IMPORTING_PRODUCER_MODULES",
)
emit(report)
