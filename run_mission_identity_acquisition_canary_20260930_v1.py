#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_ID = "MISSION-IDENTITY-ACQUISITION-CANARY-20260930-001"
MISSION_REL = "canonical/astra_runtime/missions/MISSION_IDENTITY_ACQUISITION_CANARY_20260930_001.json"
MISSION = ROOT / MISSION_REL
STATE = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"
DISCOVERY = ROOT / "canonical/astra_runtime/evidence" / f"{MISSION_ID}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
REPORT = ROOT / "mission-identity-acquisition-canary-20260930-v1-report.json"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
}

OLD_IDENTITY_ERRORS = (
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "NPM_ORIGIN_MISSION_PATH_INVALID",
    "PYTHON_SOURCE_ORIGIN_MISSION_PATH_INVALID",
)

def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def emit(payload):
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)

closure = {}
for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    closure[rel] = {"expected": expected, "observed": observed, "match": observed == expected}
    if observed != expected:
        emit({
            "schema": "PROJECT_BRAIN_MISSION_IDENTITY_ACQUISITION_CANARY_V1",
            "status": "CARRIER_CLOSURE_FAIL",
            "mission_id": MISSION_ID,
            "runtime_closure": closure,
        })
        raise SystemExit(10)

if not MISSION.is_file():
    emit({
        "schema": "PROJECT_BRAIN_MISSION_IDENTITY_ACQUISITION_CANARY_V1",
        "status": "MISSION_FILE_MISSING",
        "mission_id": MISSION_ID,
        "mission_path": MISSION_REL,
        "runtime_closure": closure,
    })
    raise SystemExit(11)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    emit({
        "schema": "PROJECT_BRAIN_MISSION_IDENTITY_ACQUISITION_CANARY_V1",
        "status": "MODEL_PLANNER_DISABLE_ENV_REQUIRED",
        "mission_id": MISSION_ID,
    })
    raise SystemExit(12)

proc = subprocess.run(
    [sys.executable, "canonical/runtime/astra_runtime.py", MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env=os.environ.copy(),
    timeout=600,
)

state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else None
discovery = json.loads(DISCOVERY.read_text(encoding="utf-8")) if DISCOVERY.is_file() else None
combined = "\n".join([
    proc.stdout or "",
    proc.stderr or "",
    json.dumps(state, sort_keys=True) if state is not None else "",
    json.dumps(discovery, sort_keys=True) if discovery is not None else "",
])

identity_errors = [x for x in OLD_IDENTITY_ERRORS if x in combined]
state_path_ok = isinstance(state, dict) and state.get("mission_path") == MISSION_REL
acquisition_attempted = (
    isinstance(discovery, dict)
    and discovery.get("source") in {"TARGETED_AUTO_ACQUISITION", "FEDERATED_CAPABILITY_DISCOVERY_FALLBACK"}
    and ("auto_acquisition" in discovery or "targeted_acquisition_error" in discovery)
)

if not state_path_ok:
    status = "CANARY_FAIL_CANONICAL_STATE_MISSION_PATH_NOT_RECORDED"
    code = 20
elif not acquisition_attempted:
    status = "CANARY_FAIL_ACQUISITION_NOT_REACHED"
    code = 21
elif identity_errors:
    status = "CANARY_FAIL_MISSION_IDENTITY_NOT_PROPAGATED"
    code = 22
else:
    status = "PASS_MISSION_IDENTITY_PROPAGATED_INTO_AUTO_ACQUISITION"
    code = 0

emit({
    "schema": "PROJECT_BRAIN_MISSION_IDENTITY_ACQUISITION_CANARY_V1",
    "status": status,
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "runtime_returncode": proc.returncode,
    "runtime_stdout_tail": (proc.stdout or "")[-12000:],
    "runtime_stderr_tail": (proc.stderr or "")[-12000:],
    "runtime_closure": closure,
    "state_path_ok": state_path_ok,
    "state_status": state.get("status") if isinstance(state, dict) else None,
    "acquisition_attempted": acquisition_attempted,
    "discovery_source": discovery.get("source") if isinstance(discovery, dict) else None,
    "discovery_status": discovery.get("status") if isinstance(discovery, dict) else None,
    "targeted_acquisition_error": discovery.get("targeted_acquisition_error") if isinstance(discovery, dict) else None,
    "auto_acquisition": discovery.get("auto_acquisition") if isinstance(discovery, dict) else None,
    "legacy_identity_errors_observed": identity_errors,
    "model_dependency_count": 0,
    "incremental_spend_usd": 0,
    "parent_promotion_authorized": False,
})

raise SystemExit(code)
