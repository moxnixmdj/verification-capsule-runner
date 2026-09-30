#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys, traceback

ROOT = pathlib.Path(__file__).resolve().parent
TASK_ID = "PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
TASK_REL = "canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_REL = "canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
TASK_PATH = ROOT / TASK_REL
MISSION_PATH = ROOT / MISSION_REL
REPORT = ROOT / "openended-sqlite-taska-canonical-cli-terminal.json"
BRAIN_MAIN = "3ce64b1abb2e6542659617563af48e44eb33f996"
CARRIER_BASE = "760b6889704c6248d0a69310bfeb62ccefe29d5f"

EXPECTED_BLOBS = {
    TASK_REL: "5d09c9eebcb09612525836e7926bdf297f4bad32",
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/capability_planner.py": "64ff65cb184f50d3336326f33cccfcc0a53301a8",
    "canonical/runtime/capability_proposal_generators.py": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py": "6385b469f1287c971217dcac58af2ffebd81f9fd",
    "canonical/runtime/bound_capabilities/grounded_executable_composition.py": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
    "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def emit(report):
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))

closure = {}
for rel, expected in EXPECTED_BLOBS.items():
    p = ROOT / rel
    observed = git_blob_sha(p) if p.is_file() else None
    closure[rel] = {"expected": expected, "observed": observed, "match": observed == expected}

base_report = {
    "schema": "PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_CANONICAL_CLI_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "carrier_base": CARRIER_BASE,
    "task_id": TASK_ID,
    "task_blob": EXPECTED_BLOBS[TASK_REL],
    "mission_path": MISSION_REL,
    "closure": closure,
    "incremental_spend_usd": 0,
    "model_planner_disabled": True,
    "source_task_replay": False,
}

if not all(x["match"] for x in closure.values()):
    emit({**base_report, "status": "CARRIER_CLOSURE_FAIL", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
mission = json.loads(MISSION_PATH.read_text(encoding="utf-8"))

if task.get("task_id") != TASK_ID or mission.get("mission_id") != TASK_ID:
    emit({**base_report, "status": "IDENTITY_MISMATCH", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

anti = task.get("anti_leakage") or {}
if any(bool(v) for v in anti.values()):
    emit({**base_report, "status": "TASK_ANTI_LEAKAGE_CONTRACT_VIOLATED", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

constraints = task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count") != 0:
    emit({**base_report, "status": "TASK_EXECUTION_CONTRACT_INVALID", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

steps = mission.get("steps") or []
mission_clean = (
    mission.get("goal") == task.get("goal_text")
    and len(steps) == 1
    and steps[0].get("adapter") == "goal"
    and steps[0].get("goal_ref") == "goal"
    and steps[0].get("allow_optional_model_planner") is False
)
if not mission_clean:
    emit({**base_report, "status": "MISSION_FREEZE_MISMATCH", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    emit({**base_report, "status": "MODEL_PLANNER_DISABLE_ENV_REQUIRED", "task_executed": False, "execution_count": 0})
    raise SystemExit(1)

state_path = ROOT / "canonical" / "astra_runtime" / "state" / f"{TASK_ID}.json"
evidence_dir = ROOT / "canonical" / "astra_runtime" / "evidence"
prior_evidence = sorted(str(p.relative_to(ROOT)) for p in evidence_dir.glob(TASK_ID + "*") if p.is_file()) if evidence_dir.is_dir() else []
if state_path.exists() or prior_evidence:
    emit({
        **base_report,
        "status": "PREEXISTING_TASK_EXECUTION_EVIDENCE__REFUSE_DUPLICATE",
        "task_executed": False,
        "execution_count": 0,
        "preexisting_state": state_path.exists(),
        "preexisting_evidence": prior_evidence,
    })
    raise SystemExit(1)

env = os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"] = "1"

try:
    proc = subprocess.run(
        [sys.executable, "canonical/runtime/astra_runtime.py", MISSION_REL],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=720,
        env=env,
    )
except Exception as exc:
    emit({
        **base_report,
        "status": "PHYSICAL_EXECUTION_EXCEPTION",
        "task_executed": True,
        "execution_count": 1,
        "exception_type": type(exc).__name__,
        "exception": str(exc),
        "traceback_excerpt": traceback.format_exc()[-12000:],
        "independent_oracle_executed": False,
    })
    raise SystemExit(2)

evidence = []
if evidence_dir.is_dir():
    for p in sorted(evidence_dir.glob(TASK_ID + "*")):
        if p.is_file():
            evidence.append({
                "path": str(p.relative_to(ROOT)),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "content_excerpt": read_text(p)[:16000],
            })

state_text = read_text(state_path)
try:
    state = json.loads(state_text) if state_text else {}
except Exception:
    state = {"_raw": state_text[:16000]}

runtime_status = state.get("status") if isinstance(state, dict) else None
producer_completed = proc.returncode == 0 and runtime_status == "COMPLETE"
blocker = state.get("blocker") if isinstance(state, dict) else None

report = {
    **base_report,
    "status": "PRODUCER_COMPLETE__PENDING_DISTINCT_ORACLE" if producer_completed else "FAIL_FIRST_CAUSAL_GAP",
    "task_executed": True,
    "execution_count": 1,
    "runtime_returncode": proc.returncode,
    "runtime_status": runtime_status,
    "first_causal_blocker": blocker,
    "stdout_excerpt": proc.stdout[-16000:],
    "stderr_excerpt": proc.stderr[-16000:],
    "state_path": str(state_path.relative_to(ROOT)) if state_path.exists() else None,
    "state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest() if state_path.exists() else None,
    "state_excerpt": state_text[:20000],
    "evidence": evidence,
    "parent_task_completed": False,
    "independent_oracle_executed": False,
    "freshness_consumed": True,
    "same_task_replay_allowed": False,
}
emit(report)
raise SystemExit(0 if producer_completed else 2)
