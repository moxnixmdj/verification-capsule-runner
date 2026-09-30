#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_REL="canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
TASK_ID="PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
REPORT=ROOT/"openended-sqlite-taska-terminal.json"
STATE=ROOT/"canonical/astra_runtime/state"/f"{TASK_ID}.json"
EVID_DIR=ROOT/"canonical/astra_runtime/evidence"
BRAIN_BASE="3ce64b1abb2e6542659617563af48e44eb33f996"
TASK_BLOB="5d09c9eebcb09612525836e7926bdf297f4bad32"
MISSION_BLOB="28eddc71a72a8a9db95ef4b59c49a43246414577"

EXPECTED_BLOBS={
  TASK_REL:TASK_BLOB,
  MISSION_REL:MISSION_BLOB,
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "canonical/runtime/independent_npm_codec_verifier.py":"06fe2fbd7d5169e2cf455868747ac7077466c221",
  "canonical/runtime/node_codec_runner.js":"2fcda55c8537051315a0d2a939c865f2442e1279",
  "canonical/runtime/python_codec_probe.py":"fc8b5005a9888422e3cb61f6cf0bd147c740ec84",
  "canonical/runtime/verify_pending_cli_binding.py":"a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
  "canonical/runtime/promote_pending_binding.py":"f100c0d1ce5a4b07af0175035c3122d816459b0b",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True,default=str))

closure={}
for rel,expected in EXPECTED_BLOBS.items():
    path=ROOT/rel
    observed=git_blob_sha(path) if path.is_file() else None
    closure[rel]={"expected":expected,"observed":observed,"match":observed==expected}

prestart={
  "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V2",
  "brain_base":BRAIN_BASE,
  "task_id":TASK_ID,
  "task_blob":TASK_BLOB,
  "mission_blob":MISSION_BLOB,
  "task_executed":False,
  "execution_count":0,
  "source_task_replay":False,
  "incremental_spend_usd":0,
  "model_planner_disabled":os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")=="1",
  "canonical_cli_required":True,
  "closure":closure,
}

if not all(v["match"] for v in closure.values()):
    prestart.update({"status":"CARRIER_CLOSURE_FAIL","replay_allowed":True})
    emit(prestart)
    raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    prestart.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"MODEL_PLANNER_DISABLE_ENV_REQUIRED","replay_allowed":True})
    emit(prestart)
    raise SystemExit(1)

task=safe_json(ROOT/TASK_REL)
mission=safe_json(ROOT/MISSION_REL)
if not isinstance(task,dict) or task.get("task_id")!=TASK_ID:
    prestart.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"TASK_IDENTITY_INVALID","replay_allowed":True})
    emit(prestart); raise SystemExit(1)
if not isinstance(mission,dict) or mission.get("mission_id")!=TASK_ID or mission.get("goal")!=task.get("goal_text"):
    prestart.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"MISSION_TASK_BINDING_INVALID","replay_allowed":True})
    emit(prestart); raise SystemExit(1)
anti=task.get("anti_leakage") or {}
if any(bool(v) for v in anti.values()):
    prestart.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"TASK_ANTI_LEAKAGE_CONTRACT_VIOLATED","replay_allowed":True})
    emit(prestart); raise SystemExit(1)
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    prestart.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"TASK_EXECUTION_CONTRACT_INVALID","replay_allowed":True})
    emit(prestart); raise SystemExit(1)

preexisting=[]
if STATE.exists():
    preexisting.append(str(STATE.relative_to(ROOT)))
if EVID_DIR.is_dir():
    preexisting.extend(str(p.relative_to(ROOT)) for p in EVID_DIR.glob(TASK_ID+"*") if p.is_file())
if preexisting:
    prestart.update({"status":"FRESHNESS_FAIL_PRESTART","preexisting_task_artifacts":sorted(preexisting),"replay_allowed":False})
    emit(prestart); raise SystemExit(1)

report=dict(prestart)
report.update({"task_executed":True,"execution_count":1,"replay_allowed":False})

proc=subprocess.run(
    [sys.executable,str(ROOT/"canonical/runtime/astra_runtime.py"),MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=840,
    env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"},
)
report["producer_returncode"]=proc.returncode
report["producer_stdout_tail"]=proc.stdout[-20000:]
report["producer_stderr_tail"]=proc.stderr[-20000:]

state=safe_json(STATE) if STATE.is_file() else None
report["producer_state"]=state
evidence=[]
if EVID_DIR.is_dir():
    for p in sorted(EVID_DIR.glob(TASK_ID+"*")):
        if p.is_file():
            try:
                raw=p.read_text(encoding="utf-8",errors="replace")
            except Exception:
                raw=""
            evidence.append({
              "path":str(p.relative_to(ROOT)),
              "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
              "content_excerpt":raw[:14000],
            })
report["evidence"]=evidence

if proc.returncode!=0 or not isinstance(state,dict) or state.get("status")!="COMPLETE":
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":(state or {}).get("blocker") or proc.stderr[-6000:] or proc.stdout[-6000:],
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(2)

history=state.get("history") or []
last_result=history[-1].get("result") if history and isinstance(history[-1],dict) else None
report["producer_result"]=last_result
prov_ok=(
    isinstance(last_result,dict)
    and last_result.get("model_dependency_count")==0
    and last_result.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
    and last_result.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
)
report["model_dependency_count"]=last_result.get("model_dependency_count") if isinstance(last_result,dict) else None
report["cognition_dependency_class"]=last_result.get("cognition_dependency_class") if isinstance(last_result,dict) else None
report["cognition_provenance_authority"]=last_result.get("cognition_provenance_authority") if isinstance(last_result,dict) else None
report["parent_task_completed"]=False
report["independent_oracle_executed"]=False

if not prov_ok:
    report.update({"status":"FAIL_COGNITION_PROVENANCE"})
    emit(report)
    raise SystemExit(3)

report.update({
  "status":"PRODUCER_COMPLETE__PENDING_INDEPENDENT_ORACLE",
  "producer_semantic_completion":True,
  "next_required_action":"RUN_INDEPENDENT_ORACLE_WITHOUT_REPLAYING_SOURCE_TASK",
})
emit(report)
