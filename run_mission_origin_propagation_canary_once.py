#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/CANARY_RUNTIME_MISSION_ORIGIN_PROPAGATION_20260930_001.json"
MISSION_PATH = ROOT / MISSION_REL
MISSION_ID = "CANARY-RUNTIME-MISSION-ORIGIN-PROPAGATION-20260930-001"
REPORT_PATH = ROOT / "mission-origin-propagation-canary-terminal.json"
STATE_PATH = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
DISCOVERY_PATH = ROOT / "canonical/astra_runtime/evidence" / (MISSION_ID + "__PLAIN_GOAL_CAPABILITY_DISCOVERY.json")
APT_DIAG_PATH = ROOT / "canonical/astra_runtime/evidence" / (MISSION_ID + "__AUTO_APT_CLI_ACQUISITION.json")

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    MISSION_REL: "e9cc53d7f7876e0bab891fb581653f225fb84d35",
}

FORBIDDEN_ORIGIN_ERRORS = (
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "APT_ORIGIN_MISSION_MISSING",
    "PYPI_ORIGIN_MISSION_MISSING",
)

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

report = {
    "schema": "PROJECT_BRAIN_MISSION_ORIGIN_PROPAGATION_CANARY_TERMINAL_V1",
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "canary_only": True,
    "parent_task": False,
    "parent_capability_credit_authorized": False,
    "frontier_capability_credit_authorized": False,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "same_canary_replay_forbidden": True,
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
            "execution_count": 0,
            "task_executed": False,
        })
        emit(report)
        raise SystemExit(10)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "PRESTART_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
    })
    emit(report)
    raise SystemExit(11)

mission = safe_json(MISSION_PATH)
constraints = mission.get("constraints") if isinstance(mission, dict) else None
if (
    not isinstance(mission, dict)
    or mission.get("mission_id") != MISSION_ID
    or not isinstance(constraints, dict)
    or constraints.get("canary_only") is not True
    or constraints.get("parent_capability_credit_authorized") is not False
    or constraints.get("frontier_capability_credit_authorized") is not False
    or constraints.get("incremental_spend_usd") != 0
    or constraints.get("model_dependency_count") != 0
    or constraints.get("same_task_replay_forbidden") is not True
):
    report.update({
        "status": "PRESTART_POLICY_FAIL",
        "first_causal_blocker": "CANARY_MISSION_CONTRACT_INVALID",
    })
    emit(report)
    raise SystemExit(12)

contaminated = [str(p.relative_to(ROOT)) for p in (STATE_PATH, DISCOVERY_PATH, APT_DIAG_PATH) if p.exists()]
if contaminated:
    report.update({
        "status": "PRESTART_FRESHNESS_FAIL",
        "first_causal_blocker": "CANARY_ID_ALREADY_HAS_RUNTIME_EVIDENCE",
        "contaminated_paths": contaminated,
    })
    emit(report)
    raise SystemExit(13)

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

state = safe_json(STATE_PATH) if STATE_PATH.is_file() else None
discovery = safe_json(DISCOVERY_PATH) if DISCOVERY_PATH.is_file() else None
apt_diag = safe_json(APT_DIAG_PATH) if APT_DIAG_PATH.is_file() else None
combined = "\n".join([
    proc.stdout or "",
    proc.stderr or "",
    json.dumps(state, sort_keys=True) if isinstance(state, dict) else "",
    json.dumps(discovery, sort_keys=True) if isinstance(discovery, dict) else "",
    json.dumps(apt_diag, sort_keys=True) if isinstance(apt_diag, dict) else "",
])

report.update({
    "runtime_returncode": int(proc.returncode),
    "runtime_stdout_tail": (proc.stdout or "")[-8000:],
    "runtime_stderr_tail": (proc.stderr or "")[-8000:],
    "state_present": STATE_PATH.is_file(),
    "discovery_evidence_present": DISCOVERY_PATH.is_file(),
    "apt_acquisition_diagnostic_present": APT_DIAG_PATH.is_file(),
    "runtime_state": state,
    "targeted_acquisition_error": (
        discovery.get("targeted_acquisition_error")
        if isinstance(discovery, dict) else None
    ),
    "apt_diagnostic_status": (
        apt_diag.get("status") if isinstance(apt_diag, dict) else None
    ),
    "origin_path_errors_observed": [x for x in FORBIDDEN_ORIGIN_ERRORS if x in combined],
    "observed_mission_sha256": sha256_file(MISSION_PATH),
})

state_path_ok = (
    isinstance(state, dict)
    and state.get("mission_path") == MISSION_REL
    and state.get("mission_sha256") == sha256_file(MISSION_PATH)
)
reached_after_origin_validation = APT_DIAG_PATH.is_file()
no_origin_error = not report["origin_path_errors_observed"]

if not state_path_ok:
    report.update({
        "status": "FAIL_MISSION_IDENTITY_STATE_BINDING",
        "first_causal_blocker": "RUNTIME_STATE_DID_NOT_BIND_EXACT_CANONICAL_MISSION_PATH_AND_DIGEST",
    })
    emit(report)
    raise SystemExit(20)

if not reached_after_origin_validation:
    report.update({
        "status": "FAIL_CANARY_DID_NOT_REACH_POST_ORIGIN_APT_ACQUISITION",
        "first_causal_blocker": "APT_DIAGNOSTIC_ABSENT__MISSION_ORIGIN_SEAM_NOT_EXERCISED",
    })
    emit(report)
    raise SystemExit(21)

if not no_origin_error:
    report.update({
        "status": "FAIL_MISSION_ORIGIN_PROPAGATION",
        "first_causal_blocker": "ORIGIN_MISSION_PATH_REJECTED",
    })
    emit(report)
    raise SystemExit(22)

report.update({
    "status": "PASS_MISSION_ORIGIN_PROPAGATION_CANARY",
    "mission_origin_propagation_verified": True,
    "proof": [
        "canonical astra_runtime state bound the exact canonical mission path and mission digest",
        "APT acquisition diagnostic exists, which is created only after auto_apt_cli_acquisition accepted and hashed the origin mission path",
        "no APT/PyPI origin-mission path invalid or missing error was observed",
    ],
    "capability_credit_delta": 0,
    "parent_credit_delta": 0,
    "next_required_action": "RECONCILE_CANARY_RECEIPT_IN_BRAIN__THEN_RECOMPUTE_FRONTIER_BEFORE_ANY_FRESH_PARENT_TASK",
})
emit(report)
