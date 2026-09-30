#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys, traceback

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/MISSION_ORIGIN_ENTRYPOINT_CANARY_20260930_V1.json"
MISSION_PATH = ROOT / MISSION_REL
MISSION_ID = "MISSION-ORIGIN-ENTRYPOINT-CANARY-20260930-V1"
REPORT = ROOT / "mission-origin-entrypoint-canary-terminal.json"
BRAIN_MAIN = "da64d00b971d5fb4e465af09f8ebb3242831f7bb"

EXPECTED_BLOBS = {
    MISSION_REL: "ee2cbd0955488e7057add7d5a3216d3f4974dfc2",
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def emit(obj):
    REPORT.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(obj, indent=2, sort_keys=True))

closure = {}
for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    closure[rel] = {"expected": expected, "observed": observed, "match": observed == expected}

if not all(item["match"] for item in closure.values()):
    emit({
        "schema": "PROJECT_BRAIN_MISSION_ORIGIN_ENTRYPOINT_CANARY_V1",
        "status": "CARRIER_CLOSURE_FAIL",
        "brain_main": BRAIN_MAIN,
        "mission_id": MISSION_ID,
        "mission_executed": False,
        "execution_count": 0,
        "closure": closure,
        "incremental_spend_usd": 0,
        "parent_capability_credit_delta": 0,
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
        timeout=600,
        env=env,
    )
except Exception as exc:
    emit({
        "schema": "PROJECT_BRAIN_MISSION_ORIGIN_ENTRYPOINT_CANARY_V1",
        "status": "CARRIER_EXECUTION_EXCEPTION",
        "brain_main": BRAIN_MAIN,
        "mission_id": MISSION_ID,
        "mission_executed": True,
        "execution_count": 1,
        "exception_type": type(exc).__name__,
        "exception": str(exc),
        "traceback_excerpt": traceback.format_exc()[-8000:],
        "closure": closure,
        "incremental_spend_usd": 0,
        "parent_capability_credit_delta": 0,
    })
    raise SystemExit(2)

apt_evidence_path = ROOT / "canonical/astra_runtime/evidence" / f"{MISSION_ID}__AUTO_APT_CLI_ACQUISITION.json"
discovery_evidence_path = ROOT / "canonical/astra_runtime/evidence" / f"{MISSION_ID}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
state_path = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"

apt_evidence = read_text(apt_evidence_path)
discovery_evidence = read_text(discovery_evidence_path)
state = read_text(state_path)
combined = "\n".join([proc.stdout, proc.stderr, apt_evidence, discovery_evidence, state])

origin_errors = [
    marker for marker in (
        "APT_ORIGIN_MISSION_PATH_INVALID",
        "APT_ORIGIN_MISSION_MISSING",
        "PYPI_ORIGIN_MISSION_PATH_INVALID",
        "PYPI_ORIGIN_MISSION_MISSING",
    )
    if marker in combined
]

origin_path_proven = apt_evidence_path.is_file()
passed = origin_path_proven and not origin_errors

if passed:
    status = "PASS_CANONICAL_MISSION_ORIGIN_PROPAGATION"
elif origin_errors:
    status = "FAIL_MISSION_ORIGIN_PROPAGATION"
else:
    status = "FAIL_ACQUISITION_PATH_NOT_REACHED"

report = {
    "schema": "PROJECT_BRAIN_MISSION_ORIGIN_ENTRYPOINT_CANARY_V1",
    "status": status,
    "brain_main": BRAIN_MAIN,
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "mission_executed": True,
    "execution_count": 1,
    "runtime_returncode": proc.returncode,
    "canonical_entrypoint_invoked": True,
    "origin_path_proven_by_post_validation_apt_evidence": origin_path_proven,
    "origin_errors": origin_errors,
    "apt_evidence_path": str(apt_evidence_path.relative_to(ROOT)) if apt_evidence_path.is_file() else None,
    "discovery_evidence_path": str(discovery_evidence_path.relative_to(ROOT)) if discovery_evidence_path.is_file() else None,
    "state_path": str(state_path.relative_to(ROOT)) if state_path.is_file() else None,
    "stdout_excerpt": proc.stdout[-12000:],
    "stderr_excerpt": proc.stderr[-12000:],
    "apt_evidence_excerpt": apt_evidence[:12000],
    "discovery_evidence_excerpt": discovery_evidence[:12000],
    "state_excerpt": state[:12000],
    "closure": closure,
    "validation_scope": "MISSION_ORIGIN_ENTRYPOINT_ONLY",
    "parent_capability_credit_delta": 0,
    "incremental_spend_usd": 0,
}
emit(report)
raise SystemExit(0 if passed else 3)
