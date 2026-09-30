#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_ID = "ASTRA-RUNTIME-MISSION-PATH-PYPI-CANARY-CBOR-001"
MISSION_REL = "canonical/astra_runtime/missions/ASTRA_RUNTIME_MISSION_PATH_PYPI_CANARY_CBOR_001.json"
MISSION_PATH = ROOT / MISSION_REL
RUNTIME_REL = "canonical/runtime/astra_runtime.py"
RUNTIME_PATH = ROOT / RUNTIME_REL
EXPECTED_RUNTIME_BLOB = "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9"
BRAIN_CANARY_COMMIT = "f94650b3727a6e35774b465312bbedc295cded2c"
BRAIN_BASE = "da64d00b971d5fb4e465af09f8ebb3242831f7bb"
REPORT = ROOT / "canonical-mission-path-pypi-canary-terminal.json"

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(obj):
    REPORT.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(obj, indent=2, sort_keys=True, default=str), flush=True)

report = {
    "schema": "PROJECT_BRAIN_CANONICAL_MISSION_PATH_PYPI_CANARY_TERMINAL_V1",
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "brain_base": BRAIN_BASE,
    "brain_canary_commit": BRAIN_CANARY_COMMIT,
    "execution_count": 0,
    "task_executed": False,
    "fresh_non_parent_canary": True,
    "parent_capability_credit_authorized": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "runtime_blob_expected": EXPECTED_RUNTIME_BLOB,
    "runtime_blob_observed": git_blob_sha(RUNTIME_PATH) if RUNTIME_PATH.is_file() else None,
}

if report["runtime_blob_observed"] != EXPECTED_RUNTIME_BLOB:
    report.update({
        "status": "PRESTART_RUNTIME_CLOSURE_FAIL",
        "replay_allowed": True,
        "replay_reason": "NO_PRODUCER_EXECUTION",
    })
    emit(report)
    raise SystemExit(1)

if not MISSION_PATH.is_file() or MISSION_PATH.parent.resolve() != (ROOT / "canonical/astra_runtime/missions").resolve():
    report.update({
        "status": "PRESTART_CANONICAL_MISSION_PATH_FAIL",
        "replay_allowed": True,
        "replay_reason": "NO_PRODUCER_EXECUTION",
    })
    emit(report)
    raise SystemExit(2)

mission = read_json(MISSION_PATH)
if not isinstance(mission, dict) or mission.get("mission_id") != MISSION_ID:
    report.update({
        "status": "PRESTART_MISSION_ID_FAIL",
        "replay_allowed": True,
        "replay_reason": "NO_PRODUCER_EXECUTION",
    })
    emit(report)
    raise SystemExit(3)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "PRESTART_MODEL_PLANNER_POLICY_FAIL",
        "replay_allowed": True,
        "replay_reason": "NO_PRODUCER_EXECUTION",
    })
    emit(report)
    raise SystemExit(4)

report["execution_count"] = 1
report["task_executed"] = True
proc = subprocess.run(
    [sys.executable, str(RUNTIME_PATH), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=480,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["runtime_returncode"] = int(proc.returncode)
report["runtime_stdout_tail"] = proc.stdout[-16000:]
report["runtime_stderr_tail"] = proc.stderr[-16000:]

state_path = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"
state = read_json(state_path) if state_path.is_file() else None
report["state_path"] = str(state_path.relative_to(ROOT))
report["state"] = state

evidence_dir = ROOT / "canonical/astra_runtime/evidence"
evidence = {}
if evidence_dir.is_dir():
    for p in sorted(evidence_dir.glob(f"{MISSION_ID}__*.json")):
        evidence[str(p.relative_to(ROOT))] = read_json(p)
report["evidence"] = evidence

combined = "\n".join([
    proc.stdout,
    proc.stderr,
    json.dumps(state, sort_keys=True, default=str),
    json.dumps(evidence, sort_keys=True, default=str),
])

forbidden_origin_errors = [
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "NPM_ORIGIN_MISSION_PATH_INVALID",
    "SOURCE_ORIGIN_MISSION_PATH_INVALID",
]
report["forbidden_origin_errors_observed"] = [
    x for x in forbidden_origin_errors if x in combined
]

state_mission_path_ok = isinstance(state, dict) and state.get("mission_path") == MISSION_REL
report["state_mission_path_ok"] = state_mission_path_ok

gap_path = f"canonical/astra_runtime/evidence/{MISSION_ID}__GOAL_GAP_CLASSIFICATION.json"
gap = evidence.get(gap_path)
gap_acquisition_eligible = (
    isinstance(gap, dict)
    and gap.get("gap_class") == "CAPABILITY_CANDIDATE"
    and gap.get("capability_acquisition_allowed") is True
)
report["gap_acquisition_eligible"] = gap_acquisition_eligible

acquisition_markers = [
    "AUTO_PYPI_LIBRARY_ACQUISITION",
    "AUTO_ACQUISITION_DISPATCHED",
    "NO_COMPATIBLE_REQUIRED_SUPPLIER_CONTRACT",
    "NO_COMPATIBLE_PYPI_LIBRARY_CONTRACT",
    "NO_BOUNDED_PYPI_CANDIDATE",
    "CAPABILITY_ACQUISITION_REQUIRED",
    "pypi_python_library",
]
report["acquisition_markers_observed"] = [x for x in acquisition_markers if x in combined]

full_complete = (
    proc.returncode == 0
    and isinstance(state, dict)
    and state.get("status") == "COMPLETE"
)
seam_qualified = (
    state_mission_path_ok
    and gap_acquisition_eligible
    and bool(report["acquisition_markers_observed"])
    and not report["forbidden_origin_errors_observed"]
)

if full_complete and not report["forbidden_origin_errors_observed"]:
    report.update({
        "status": "PASS_FULL_NONPARENT_CANARY",
        "public_runtime_cli_boundary_qualified": True,
        "runtime_mission_identity_propagation_qualified": True,
        "replay_allowed": False,
        "next_action": "RECONCILE_RECEIPT_THEN_FREEZE_MATERIALLY_DIFFERENT_FRESH_OPEN_ENDED_PARENT_TASK_A",
    })
    emit(report)
    raise SystemExit(0)

if seam_qualified:
    report.update({
        "status": "PASS_MISSION_PATH_PROPAGATION_SEAM__LATER_GAP_REMAINS",
        "public_runtime_cli_boundary_qualified": True,
        "runtime_mission_identity_propagation_qualified": True,
        "replay_allowed": False,
        "next_action": "RECONCILE_RECEIPT_AND_LOCALIZE_ONLY_THE_LATER_TERMINAL_GAP_BEFORE_FRESH_PARENT_TASK_A",
    })
    emit(report)
    raise SystemExit(0)

report.update({
    "status": "FAIL_CANARY_DECISIVE_SEAM_NOT_PROVEN",
    "public_runtime_cli_boundary_qualified": False,
    "runtime_mission_identity_propagation_qualified": False,
    "replay_allowed": False,
})
emit(report)
raise SystemExit(5)
