#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
TASK_ID = "PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
TASK_REL = "canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_REL = "canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
REPORT = ROOT / "frozen-sqlite-openended-taska-producer-terminal.json"
STDOUT = ROOT / "frozen-sqlite-openended-taska.stdout"
STDERR = ROOT / "frozen-sqlite-openended-taska.stderr"
BRAIN_MAIN = "3ce64b1abb2e6542659617563af48e44eb33f996"
RUNNER_MAIN = "eff796468741f509650904cd7fbaf8eab3958ff1"

EXPECTED_BLOBS = {
    TASK_REL: "5d09c9eebcb09612525836e7926bdf297f4bad32",
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
}

def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str), flush=True)

base = {
    "schema": "PROJECT_BRAIN_FROZEN_SQLITE_OPENENDED_TASK_A_PRODUCER_TERMINAL_V1",
    "task_id": TASK_ID,
    "brain_main_at_freeze": BRAIN_MAIN,
    "runner_main_at_branch": RUNNER_MAIN,
    "source_task_path": TASK_REL,
    "mission_path": MISSION_REL,
    "incremental_spend_usd": 0,
    "model_planner_disabled": True,
    "execution_count": 0,
    "task_executed": False,
    "independent_oracle_executed": False,
}

for rel, expected in EXPECTED_BLOBS.items():
    p = ROOT / rel
    observed = git_blob_sha(p) if p.is_file() else None
    if observed != expected:
        report = dict(base)
        report.update({
            "status": "CARRIER_CLOSURE_FAIL_PRESTART",
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
        })
        emit(report)
        raise SystemExit(10)

task = json.loads((ROOT / TASK_REL).read_text(encoding="utf-8"))
mission = json.loads((ROOT / MISSION_REL).read_text(encoding="utf-8"))

if task.get("task_id") != TASK_ID or mission.get("mission_id") != TASK_ID:
    report = dict(base)
    report.update({"status": "IDENTITY_FAIL_PRESTART"})
    emit(report)
    raise SystemExit(11)

if str(task.get("goal_text") or "").strip() != str(mission.get("goal") or "").strip():
    report = dict(base)
    report.update({"status": "GOAL_MIRROR_FAIL_PRESTART"})
    emit(report)
    raise SystemExit(12)

constraints = task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count") != 0:
    report = dict(base)
    report.update({"status": "TASK_CONTRACT_FAIL_PRESTART", "execution_constraints": constraints})
    emit(report)
    raise SystemExit(13)

state_path = ROOT / "canonical" / "astra_runtime" / "state" / f"{TASK_ID}.json"
receipt_path = ROOT / "canonical" / "astra_runtime" / "evidence" / f"{TASK_ID}__RECEIPT.json"
if state_path.exists():
    report = dict(base)
    report.update({"status": "PREEXISTING_RUNTIME_STATE_REFUSES_EXECUTION"})
    emit(report)
    raise SystemExit(14)

env = os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"] = "1"
cmd = [sys.executable, str(ROOT / "canonical" / "runtime" / "astra_runtime.py"), MISSION_REL]

proc = subprocess.run(
    cmd,
    cwd=ROOT,
    text=True,
    capture_output=True,
    env=env,
    timeout=900,
)
STDOUT.write_text(proc.stdout, encoding="utf-8")
STDERR.write_text(proc.stderr, encoding="utf-8")

state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
history = state.get("history") if isinstance(state.get("history"), list) else []
last_result = history[-1].get("result") if history and isinstance(history[-1], dict) else None
if not isinstance(last_result, dict):
    last_result = {}

report = dict(base)
report.update({
    "execution_count": 1,
    "task_executed": True,
    "runtime_returncode": proc.returncode,
    "runtime_status": state.get("status"),
    "runtime_next_step": state.get("next_step"),
    "runtime_blocker": state.get("blocker"),
    "runtime_history_count": len(history),
    "runtime_result": last_result or None,
    "receipt_present": receipt_path.is_file(),
})

success = (
    proc.returncode == 0
    and state.get("status") == "COMPLETE"
    and bool(history)
    and history[-1].get("ok") is True
    and last_result.get("model_dependency_count") == 0
    and last_result.get("cognition_provenance_authority") == "ASTRA_RUNTIME_DERIVED_V1"
    and not str(last_result.get("controller_mode") or "").startswith("OPTIONAL_MODEL_ADVISORY")
    and last_result.get("planner_model_last") in (None, "")
)

if success:
    report.update({
        "status": "PRODUCER_SUCCESS_PENDING_INDEPENDENT_VERIFICATION",
        "parent_task_completed": True,
        "runtime_derived_model_dependency_count": last_result.get("model_dependency_count"),
        "cognition_provenance_authority": last_result.get("cognition_provenance_authority"),
    })
    emit(report)
    raise SystemExit(0)

corpus = "\n".join([
    proc.stdout[-8000:],
    proc.stderr[-8000:],
    json.dumps(state.get("blocker"), sort_keys=True, default=str) if state.get("blocker") else "",
])
report.update({
    "status": "FAIL_FIRST_CAUSAL_GAP",
    "parent_task_completed": False,
    "first_causal_blocker": state.get("blocker") or corpus[-12000:],
})
emit(report)
raise SystemExit(2)
