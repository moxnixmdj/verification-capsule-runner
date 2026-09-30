#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/NONPARENT_MISSION_PATH_APT_CANARY_20260930_001.json"
MISSION_PATH = ROOT / MISSION_REL
MISSION_ID = "NONPARENT-MISSION-PATH-APT-CANARY-20260930-001"
REPORT = ROOT / "mission-path-apt-canary-terminal.json"
BRAIN_MAIN = "da64d00b971d5fb4e465af09f8ebb3242831f7bb"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
}

INVALID_MARKERS = (
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "APT_ORIGIN_MISSION_MISSING",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_MISSING",
)

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(obj):
    REPORT.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(obj, indent=2, sort_keys=True, default=str), flush=True)

report = {
    "schema": "PROJECT_BRAIN_NONPARENT_MISSION_PATH_APT_CANARY_V1",
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "brain_main": BRAIN_MAIN,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "parent_capability_credit_authorized": False,
    "task_class": "NON_PARENT_CANARY",
    "execution_count": 0,
}

for rel, expected in EXPECTED_BLOBS.items():
    p = ROOT / rel
    observed = git_blob_sha(p) if p.is_file() else None
    if observed != expected:
        report.update(status="CARRIER_CLOSURE_FAIL", path=rel, expected_blob=expected, observed_blob=observed)
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update(status="POLICY_FAIL", first_causal_blocker="MODEL_PLANNER_NOT_DISABLED")
    emit(report)
    raise SystemExit(1)

if not MISSION_PATH.is_file() or MISSION_PATH.parent.resolve() != (ROOT / "canonical/astra_runtime/missions").resolve():
    report.update(status="POLICY_FAIL", first_causal_blocker="MISSION_NOT_DIRECT_CHILD_OF_CANONICAL_MISSIONS")
    emit(report)
    raise SystemExit(1)

mission = read_json(MISSION_PATH)
if not isinstance(mission, dict) or mission.get("mission_id") != MISSION_ID:
    report.update(status="POLICY_FAIL", first_causal_blocker="MISSION_ID_OR_JSON_INVALID")
    emit(report)
    raise SystemExit(1)

state_path = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
evidence_dir = ROOT / "canonical/astra_runtime/evidence"
preexisting = []
for p in [state_path, evidence_dir / (MISSION_ID + "__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"), evidence_dir / (MISSION_ID + "__AUTO_APT_CLI_ACQUISITION.json")]:
    if p.exists():
        preexisting.append(str(p.relative_to(ROOT)))
if preexisting:
    report.update(status="FRESHNESS_FAIL", preexisting=preexisting)
    emit(report)
    raise SystemExit(1)

report["mission_sha256"] = sha256(MISSION_PATH)
report["execution_count"] = 1

proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=600,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["runtime_returncode"] = proc.returncode
report["runtime_stdout_tail"] = proc.stdout[-12000:]
report["runtime_stderr_tail"] = proc.stderr[-12000:]

state = read_json(state_path) if state_path.is_file() else None
report["runtime_state"] = state
report["runtime_state_mission_path"] = state.get("mission_path") if isinstance(state, dict) else None

plain_ep = evidence_dir / (MISSION_ID + "__PLAIN_GOAL_CAPABILITY_DISCOVERY.json")
apt_ep = evidence_dir / (MISSION_ID + "__AUTO_APT_CLI_ACQUISITION.json")
plain = read_json(plain_ep) if plain_ep.is_file() else None
apt = read_json(apt_ep) if apt_ep.is_file() else None
report["plain_goal_discovery_evidence_present"] = plain_ep.is_file()
report["apt_acquisition_evidence_present"] = apt_ep.is_file()
report["plain_goal_discovery_evidence"] = plain
report["apt_acquisition_evidence"] = apt

all_text = json.dumps(report, sort_keys=True, default=str)
invalid = [m for m in INVALID_MARKERS if m in all_text]
report["origin_identity_invalid_markers"] = invalid

# Strong proof: auto_apt_cli_acquisition.dispatch computes and validates
# _origin_mission_sha256() before it creates this APT evidence file.
if apt_ep.is_file() and not invalid and report["runtime_state_mission_path"] == MISSION_REL:
    report.update(
        status="PASS_MISSION_PATH_PROPAGATION_CANARY",
        mission_path_boundary_validated=True,
        proof="APT evidence exists only after canonical mission-path validation; runtime state preserves the same canonical mission path.",
        parent_capability_credit_authorized=False,
        next_required_action="FREEZE_MATERIALLY_DIFFERENT_FRESH_OPEN_ENDED_TASK_A_ON_CURRENT_BRAIN_AUTHORITY",
    )
    emit(report)
    raise SystemExit(0)

# If APT evidence was not emitted, preserve the exact deeper blocker but do not
# pretend the mission-path seam was validated.
report.update(
    status="FAIL_CANARY_NOT_PROVEN",
    mission_path_boundary_validated=False,
    parent_capability_credit_authorized=False,
)
emit(report)
raise SystemExit(2)
