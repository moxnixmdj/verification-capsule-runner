#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/NONPARENT_MISSION_PATH_PYPI_AVRO_CANARY_20260930_001.json"
MISSION_PATH = ROOT / MISSION_REL
MISSION_ID = "NONPARENT-MISSION-PATH-PYPI-AVRO-CANARY-20260930-001"
REPORT_PATH = ROOT / "nonparent-mission-path-pypi-avro-canary-terminal.json"
BRAIN_MAIN = "da64d00b971d5fb4e465af09f8ebb3242831f7bb"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    MISSION_REL: "437382df0cb0b6c095d42767af22d0bcade82106",
}
FORBIDDEN_PATH_ERRORS = (
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
)

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

report = {
    "schema": "PROJECT_BRAIN_NONPARENT_MISSION_PATH_CANARY_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "non_parent_canary": True,
    "parent_capability_credit_authorized": False,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
}

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        report.update({
            "status": "PRESTART_CARRIER_CLOSURE_FAIL",
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
        })
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "PRESTART_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
    })
    emit(report)
    raise SystemExit(1)

mission = safe_json(MISSION_PATH)
if not isinstance(mission, dict) or mission.get("mission_id") != MISSION_ID:
    report.update({
        "status": "PRESTART_MISSION_FAIL",
        "first_causal_blocker": "MISSION_ID_OR_JSON_INVALID",
    })
    emit(report)
    raise SystemExit(1)

constraints = mission.get("constraints") or {}
if (
    constraints.get("incremental_spend_usd") != 0
    or constraints.get("model_dependency_count") != 0
    or constraints.get("non_parent_canary") is not True
    or constraints.get("parent_capability_credit_authorized") is not False
    or constraints.get("canonical_cli_entrypoint_required") is not True
    or constraints.get("auto_acquisition_path_required") is not True
    or constraints.get("mission_path_error_forbidden") is not True
):
    report.update({
        "status": "PRESTART_MISSION_FAIL",
        "first_causal_blocker": "MISSION_CONSTRAINT_CONTRACT_INVALID",
    })
    emit(report)
    raise SystemExit(1)

report["mission_sha256"] = sha256_file(MISSION_PATH)
report["execution_count"] = 1
report["task_executed"] = True

proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=480,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["runtime_returncode"] = int(proc.returncode)
report["runtime_stdout_tail"] = proc.stdout[-12000:]
report["runtime_stderr_tail"] = proc.stderr[-12000:]

state_path = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
state = safe_json(state_path) if state_path.is_file() else None
report["runtime_state"] = state

evid_dir = ROOT / "canonical/astra_runtime/evidence"
evidence = {}
if evid_dir.is_dir():
    for p in sorted(evid_dir.glob(MISSION_ID + "*")):
        if p.is_file():
            evidence[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8", errors="replace")[-20000:]
report["evidence_files"] = sorted(evidence)

combined = "\n".join([
    proc.stdout,
    proc.stderr,
    json.dumps(state, sort_keys=True, default=str),
    *evidence.values(),
])
path_errors = [marker for marker in FORBIDDEN_PATH_ERRORS if marker in combined]
report["forbidden_path_errors_observed"] = path_errors

if not isinstance(state, dict):
    report.update({
        "status": "FAIL_CANARY_NO_RUNTIME_STATE",
        "first_causal_blocker": "RUNTIME_STATE_MISSING",
    })
    emit(report)
    raise SystemExit(2)

if state.get("mission_path") != MISSION_REL:
    report.update({
        "status": "FAIL_CANARY_MISSION_PATH_NOT_STORED",
        "first_causal_blocker": "STATE_MISSION_PATH_MISMATCH",
        "observed_mission_path": state.get("mission_path"),
    })
    emit(report)
    raise SystemExit(2)

if state.get("mission_sha256") != report["mission_sha256"]:
    report.update({
        "status": "FAIL_CANARY_MISSION_HASH_NOT_BOUND",
        "first_causal_blocker": "STATE_MISSION_SHA256_MISMATCH",
        "observed_mission_sha256": state.get("mission_sha256"),
    })
    emit(report)
    raise SystemExit(2)

if path_errors:
    report.update({
        "status": "FAIL_CANARY_PATH_PROPAGATION",
        "first_causal_blocker": "ORIGIN_MISSION_PATH_INVALID_RECURRED",
    })
    emit(report)
    raise SystemExit(2)

discovery_path = evid_dir / (MISSION_ID + "__PLAIN_GOAL_CAPABILITY_DISCOVERY.json")
discovery = safe_json(discovery_path) if discovery_path.is_file() else None
report["capability_discovery_evidence"] = discovery

if not isinstance(discovery, dict):
    report.update({
        "status": "FAIL_CANARY_DID_NOT_REACH_AUTO_ACQUISITION",
        "first_causal_blocker": "PLAIN_GOAL_CAPABILITY_DISCOVERY_EVIDENCE_MISSING",
    })
    emit(report)
    raise SystemExit(3)

auto = discovery.get("auto_acquisition")
targeted_error = str(discovery.get("targeted_acquisition_error") or "")
auto_error = ""
supplier_class = None
if isinstance(auto, dict):
    auto_error = str(auto.get("error") or "")
    supplier_class = auto.get("supplier_class")

pypi_evidence_present = any(
    name.endswith("__AUTO_PYPI_LIBRARY_ACQUISITION.json")
    for name in evidence
)
supplier_signal_blob = "\n".join([
    targeted_error,
    auto_error,
    json.dumps(auto, sort_keys=True, default=str),
]).lower()
pypi_route_observed = (
    supplier_class == "pypi_python_library"
    or "pypi" in supplier_signal_blob
    or pypi_evidence_present
)
report["pypi_route_observed"] = bool(pypi_route_observed)
report["targeted_acquisition_error"] = targeted_error
report["fallback_auto_acquisition_error"] = auto_error
report["pypi_acquisition_evidence_present"] = pypi_evidence_present

if not pypi_route_observed:
    report.update({
        "status": "FAIL_CANARY_NO_PYPI_SUPPLIER_SIGNAL",
        "first_causal_blocker": "AUTO_ACQUISITION_REACHED_BUT_PYPI_ROUTE_NOT_OBSERVED",
    })
    emit(report)
    raise SystemExit(4)

report.update({
    "status": "PASS_CANONICAL_CLI_PROPAGATES_MISSION_PATH_TO_AUTO_ACQUISITION",
    "mission_path_propagated": True,
    "origin_mission_path_invalid_absent": True,
    "auto_acquisition_reached": True,
    "model_dependency_count": 0,
    "incremental_spend_usd": 0,
    "parent_capability_credit_authorized": False,
    "next_required_action": "RECONCILE_CANARY_RECEIPT_IN_CANONICAL_BRAIN_THEN_FREEZE_ONE_MATERIALLY_DIFFERENT_FRESH_OPEN_ENDED_PARENT_TASK_A",
})
emit(report)
raise SystemExit(0)
