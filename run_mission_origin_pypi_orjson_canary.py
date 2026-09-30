#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/ASTRA_RUNTIME_MISSION_ORIGIN_PYPI_ORJSON_CANARY_20260930_001.json"
MISSION_ID = "ASTRA-RUNTIME-MISSION-ORIGIN-PYPI-ORJSON-CANARY-20260930-001"
SOURCE_REL = "canonical/astra_runtime/tmp/ORJSON_ORIGIN_CANARY_SOURCE.txt"
REPORT_PATH = ROOT / "mission-origin-pypi-orjson-canary-terminal.json"
BASE_MAIN = "eff796468741f509650904cd7fbaf8eab3958ff1"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    MISSION_REL: "2627820e0ea43e95e90c26ac4b33fceae3da474b",
    SOURCE_REL: "017563408d0422199cbd1dee6e737ed6f4c0bfbb",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def registry_entries(registry):
    if not isinstance(registry, dict):
        return {}
    caps = registry.get("capabilities")
    return caps if isinstance(caps, dict) else registry

report = {
    "schema": "PROJECT_BRAIN_MISSION_ORIGIN_PYPI_ORJSON_CANARY_TERMINAL_V1",
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "base_runner_main": BASE_MAIN,
    "execution_count": 0,
    "task_executed": False,
    "non_parent_canary": True,
    "parent_capability_credit_authorized": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
}

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        report.update({"status":"CARRIER_CLOSURE_FAIL","path":rel,"expected_blob":expected,"observed_blob":observed,"replay_allowed":True})
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"MODEL_PLANNER_NOT_DISABLED","replay_allowed":True})
    emit(report)
    raise SystemExit(1)

pre_registry_path = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
pre_registry = safe_json(pre_registry_path) or {}
pre_orjson = []
for cid, entry in registry_entries(pre_registry).items():
    if not isinstance(entry, dict):
        continue
    blob = json.dumps(entry, sort_keys=True).lower()
    if "orjson" in blob:
        pre_orjson.append(cid)
report["prestart_orjson_capability_ids"] = sorted(pre_orjson)
if pre_orjson:
    report.update({"status":"FRESHNESS_FAIL_PRESTART","first_causal_blocker":"ORJSON_ALREADY_BOUND","replay_allowed":False})
    emit(report)
    raise SystemExit(1)

state_path = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"
evidence_path = ROOT / "canonical/astra_runtime/evidence" / f"{MISSION_ID}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
if state_path.exists() or evidence_path.exists():
    report.update({"status":"FRESHNESS_FAIL_PRESTART","preexisting_state":state_path.exists(),"preexisting_discovery_evidence":evidence_path.exists(),"replay_allowed":False})
    emit(report)
    raise SystemExit(1)

report["execution_count"] = 1
report["task_executed"] = True
proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=600,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["producer_returncode"] = int(proc.returncode)
report["producer_stdout_tail"] = proc.stdout[-16000:]
report["producer_stderr_tail"] = proc.stderr[-16000:]

state = safe_json(state_path) if state_path.is_file() else None
discovery = safe_json(evidence_path) if evidence_path.is_file() else None
report["producer_state"] = state
report["capability_discovery_evidence"] = discovery
report["state_mission_path"] = (state or {}).get("mission_path")

all_text = "\n".join([
    proc.stdout, proc.stderr,
    json.dumps(state, sort_keys=True) if state is not None else "",
    json.dumps(discovery, sort_keys=True) if discovery is not None else "",
])
origin_tokens = [
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "NPM_ORIGIN_MISSION_PATH_INVALID",
    "PYTHON_SOURCE_ORIGIN_MISSION_PATH_INVALID",
]
origin_errors = [x for x in origin_tokens if x in all_text]
report["observed_origin_path_errors"] = origin_errors

post_registry = safe_json(pre_registry_path) or {}
observed = []
for cid, entry in registry_entries(post_registry).items():
    if not isinstance(entry, dict):
        continue
    source = entry.get("source") or {}
    provides = [str(x).lower() for x in (entry.get("provides") or [])]
    verification = entry.get("verification") or {}
    if str(source.get("type") or "").lower() != "pypi":
        continue
    if "structured.binary.encode.orjson" not in provides and "orjson" not in str(cid).lower() and "orjson" not in str(source.get("project") or "").lower():
        continue
    vmid = str(verification.get("mission_id") or "")
    vstate_path = ROOT / "canonical/astra_runtime/state" / f"{vmid}.json" if vmid else None
    vstate = safe_json(vstate_path) if vstate_path and vstate_path.is_file() else None
    observed.append({
        "capability_id": cid,
        "project": source.get("project"),
        "version": source.get("version"),
        "status": entry.get("status"),
        "provides": entry.get("provides"),
        "independent_verified": verification.get("independent_verified"),
        "verification_mission_id": vmid,
        "verification_state_status": (vstate or {}).get("status"),
    })
report["observed_pypi_orjson_capabilities"] = observed

if origin_errors or report["state_mission_path"] != MISSION_REL:
    report.update({
        "status":"FAIL_CANONICAL_MISSION_ORIGIN_BRIDGE",
        "canonical_mission_origin_validated":False,
        "verified_acquisition_observed":False,
        "replay_allowed":False,
    })
    emit(report)
    raise SystemExit(2)

report["canonical_mission_origin_validated"] = True
verified = [
    x for x in observed
    if x.get("status") == "VERIFIED_BOUND_CAPABILITY"
    and x.get("independent_verified") is True
    and x.get("verification_state_status") == "COMPLETE"
]
report["verified_orjson_acquisitions"] = verified

if not verified:
    report.update({
        "status":"FAIL_VERIFIED_PYPI_ORJSON_ACQUISITION_NOT_OBSERVED",
        "verified_acquisition_observed":False,
        "first_deeper_blocker":(state or {}).get("blocker") or proc.stderr[-4000:] or proc.stdout[-4000:],
        "replay_allowed":False,
    })
    emit(report)
    raise SystemExit(3)

report.update({
    "status":"PASS_CANONICAL_MISSION_ORIGIN_AND_VERIFIED_PYPI_ACQUISITION",
    "verified_acquisition_observed":True,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
    "parent_capability_credit_authorized":False,
    "post_acquisition_parent_goal_completion_required_for_this_canary":False,
    "producer_runtime_complete": isinstance(state, dict) and state.get("status") == "COMPLETE",
    "replay_allowed":False,
    "next_required_action":"RECONCILE_CANARY_RECEIPT_IN_CANONICAL_BRAIN__THEN_FREEZE_MATERIALLY_DIFFERENT_FRESH_OPEN_ENDED_PARENT_TASK_A",
})
emit(report)
