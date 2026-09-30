#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/ASTRA_RUNTIME_MISSION_ORIGIN_PYPI_CBOR_CANARY_20260930_001.json"
MISSION_ID = "ASTRA-RUNTIME-MISSION-ORIGIN-PYPI-CBOR-CANARY-20260930-001"
REPORT_PATH = ROOT / "mission-origin-pypi-cbor-canary-terminal.json"
BASE_MAIN = "9d89db132108fde5882831a01b311f7abc7e5de4"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    MISSION_REL: "61b3843e839be4a254c2f1c691608a86f07e6cbf",
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

def find_model_counts(value):
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "model_dependency_count":
                try: out.append(int(v))
                except Exception: out.append(-1)
            out.extend(find_model_counts(v))
    elif isinstance(value, list):
        for item in value:
            out.extend(find_model_counts(item))
    return out

report = {
    "schema": "PROJECT_BRAIN_MISSION_ORIGIN_PYPI_CBOR_CANARY_TERMINAL_V1",
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
        report.update({
            "status": "CARRIER_CLOSURE_FAIL",
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
            "replay_allowed": True,
            "replay_reason": "PRESTART_CARRIER_CLOSURE_FAILURE",
        })
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
        "replay_allowed": True,
        "replay_reason": "PRESTART_POLICY_FAILURE",
    })
    emit(report)
    raise SystemExit(1)

mission = safe_json(ROOT / MISSION_REL)
constraints = (mission or {}).get("constraints") or {}
if (
    not isinstance(mission, dict)
    or mission.get("mission_id") != MISSION_ID
    or constraints.get("incremental_spend_usd") != 0
    or constraints.get("model_dependency_count") != 0
    or constraints.get("non_parent_canary") is not True
    or constraints.get("parent_capability_credit_authorized") is not False
    or constraints.get("canonical_mission_entrypoint_required") is not True
):
    report.update({
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MISSION_CONSTRAINT_CONTRACT_INVALID",
        "replay_allowed": True,
        "replay_reason": "PRESTART_MISSION_CONTRACT_FAILURE",
    })
    emit(report)
    raise SystemExit(1)

state_path = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"
evidence_path = ROOT / "canonical/astra_runtime/evidence" / f"{MISSION_ID}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
if state_path.exists() or evidence_path.exists():
    report.update({
        "status": "FRESHNESS_FAIL_PRESTART",
        "preexisting_state": state_path.exists(),
        "preexisting_discovery_evidence": evidence_path.exists(),
        "replay_allowed": False,
    })
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

all_text = "\n".join([
    proc.stdout,
    proc.stderr,
    json.dumps(state, sort_keys=True) if state is not None else "",
    json.dumps(discovery, sort_keys=True) if discovery is not None else "",
])
origin_error_tokens = [
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "NPM_ORIGIN_MISSION_PATH_INVALID",
    "PYTHON_SOURCE_ORIGIN_MISSION_PATH_INVALID",
]
observed_origin_errors = [x for x in origin_error_tokens if x in all_text]
report["observed_origin_path_errors"] = observed_origin_errors
report["state_mission_path"] = (state or {}).get("mission_path")

registry = safe_json(ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json") or {}
entries = registry.get("capabilities") if isinstance(registry.get("capabilities"), dict) else registry
pypi_cbor = []
if isinstance(entries, dict):
    for cid, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") or {}
        provides = [str(x).lower() for x in (entry.get("provides") or [])]
        if str(source.get("type") or "").lower() == "pypi" and "structured.binary.encode.cbor" in provides:
            pypi_cbor.append({
                "capability_id": cid,
                "project": source.get("project"),
                "version": source.get("version"),
                "status": entry.get("status"),
                "independent_verified": ((entry.get("verification") or {}).get("independent_verified")),
            })
report["observed_pypi_cbor_capabilities"] = pypi_cbor

if observed_origin_errors or report["state_mission_path"] != MISSION_REL:
    report.update({
        "status": "FAIL_CANONICAL_MISSION_ORIGIN_BRIDGE",
        "canonical_mission_origin_validated": False,
        "replay_allowed": False,
        "parent_capability_credit_authorized": False,
    })
    emit(report)
    raise SystemExit(2)

report["canonical_mission_origin_validated"] = True

if proc.returncode != 0 or not isinstance(state, dict) or state.get("status") != "COMPLETE":
    report.update({
        "status": "PASS_MISSION_ORIGIN_BRIDGE__DEEPER_CANARY_BLOCKER",
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_deeper_blocker": (state or {}).get("blocker") or proc.stderr[-4000:] or proc.stdout[-4000:],
    })
    emit(report)
    raise SystemExit(3)

model_counts = find_model_counts(state)
report["observed_model_dependency_counts"] = model_counts
if any(v != 0 for v in model_counts):
    report.update({
        "status": "FAIL_MODEL_INDEPENDENCE_AFTER_ORIGIN_PASS",
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(4)

source_path = ROOT / "canonical/astra_runtime/tmp/MISSION_ORIGIN_CBOR_CANARY_SOURCE.json"
output_path = ROOT / "canonical/astra_runtime/tmp/MISSION_ORIGIN_CBOR_CANARY_OUTPUT.cbor"
report["source_artifact_exists"] = source_path.is_file()
report["output_artifact_exists"] = output_path.is_file()
report["output_artifact_bytes"] = output_path.stat().st_size if output_path.is_file() else 0

if not pypi_cbor or not source_path.is_file() or not output_path.is_file():
    report.update({
        "status": "FAIL_EXPECTED_PYPI_CBOR_ACQUISITION_NOT_OBSERVED",
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(5)

report.update({
    "status": "PASS_CANONICAL_MISSION_ORIGIN_AND_PYPI_ACQUISITION",
    "canonical_mission_origin_validated": True,
    "model_dependency_count": 0,
    "incremental_spend_usd": 0,
    "parent_capability_credit_authorized": False,
    "replay_allowed": False,
    "next_required_action": "RECONCILE_CANARY_RECEIPT_IN_CANONICAL_BRAIN__THEN_FREEZE_MATERIALLY_DIFFERENT_FRESH_OPEN_ENDED_PARENT_TASK_A",
})
emit(report)
