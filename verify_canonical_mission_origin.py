#!/usr/bin/env python3
import hashlib
import importlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "canonical" / "runtime"
MISSION_REL = "canonical/astra_runtime/missions/NONPARENT_MISSION_ORIGIN_QUALIFICATION_20260930_V1.json"
MISSION_PATH = ROOT / MISSION_REL
MISSION_ID = "NONPARENT-MISSION-ORIGIN-QUALIFICATION-20260930-V1"
REPORT_PATH = ROOT / "canonical-mission-origin-qualification-report.json"
BRAIN_MAIN = "da64d00b971d5fb4e465af09f8ebb3242831f7bb"
RUNNER_MAIN = "9d89db132108fde5882831a01b311f7abc7e5de4"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/auto_npm_library_acquisition.py": "b74cdf34a96fc2d591b902e1d582e0381a8a8d08",
    "canonical/runtime/auto_python_source_codec_acquisition.py": "65453b2eed5e678def3f0ab1c4d44182fb0b9a78",
}

def git_blob_sha(path):
    raw = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256_file(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def fail(code, detail=None):
    report = {
        "schema": "PROJECT_BRAIN_CANONICAL_MISSION_ORIGIN_QUALIFICATION_V1",
        "status": "FAIL",
        "failure": code,
        "detail": detail,
        "brain_main": BRAIN_MAIN,
        "runner_main": RUNNER_MAIN,
        "mission_id": MISSION_ID,
        "parent_task_executed": False,
        "supplier_dispatch_executed": False,
        "network_supplier_discovery_executed": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "capability_credit_authorized": False,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(1)

def require(condition, code, detail=None):
    if not condition:
        fail(code, detail)

def load_runtime_module():
    path = RUNTIME_DIR / "astra_runtime.py"
    spec = importlib.util.spec_from_file_location("mission_origin_qualification_runtime", path)
    require(spec is not None and spec.loader is not None, "RUNTIME_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def expect_failure(callable_, accepted_prefixes, label):
    try:
        callable_()
    except Exception as exc:
        message = str(exc)
        require(
            any(message.startswith(prefix) for prefix in accepted_prefixes),
            "NEGATIVE_CONTROL_WRONG_FAILURE",
            {"label": label, "message": message, "accepted_prefixes": accepted_prefixes},
        )
        return message
    fail("NEGATIVE_CONTROL_DID_NOT_FAIL", label)

def cleanup(runtime):
    state = runtime.STATE_DIR / (MISSION_ID + ".json")
    receipt = runtime.EVID_DIR / (MISSION_ID + "__RECEIPT.json")
    blocker = runtime.EVID_DIR / (MISSION_ID + "__BLOCKER.json")
    drift = runtime.EVID_DIR / (MISSION_ID + "__MISSION_DRIFT_BLOCKER.json")
    for path in (state, receipt, blocker, drift):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

def main():
    require(MISSION_PATH.is_file(), "MISSION_FILE_MISSING", MISSION_REL)

    observed_blobs = {}
    for rel, expected in EXPECTED_BLOBS.items():
        path = ROOT / rel
        require(path.is_file(), "CLOSURE_FILE_MISSING", rel)
        observed = git_blob_sha(path)
        observed_blobs[rel] = observed
        require(observed == expected, "CLOSURE_BLOB_MISMATCH", {
            "path": rel, "expected": expected, "observed": observed
        })

    runtime_text = (RUNTIME_DIR / "astra_runtime.py").read_text(encoding="utf-8")
    static_requirements = {
        "cli_path_canonicalization": 'mission_path,mission_rel=_canonical_mission_path(a.mission)',
        "runtime_path_injection": 'mission["_runtime_mission_path"]=mission_rel',
        "acquisition_reads_runtime_path": 'str(mission.get("_runtime_mission_path") or "")',
    }
    for label, needle in static_requirements.items():
        require(needle in runtime_text, "STATIC_ROUTE_REQUIREMENT_MISSING", {
            "label": label, "needle": needle
        })

    runtime = load_runtime_module()
    cleanup(runtime)

    boundary = {}
    def intercepted_execute_step(step, prior_results=None, mission=None):
        boundary["step_id"] = step.get("id")
        boundary["mission_id"] = (mission or {}).get("mission_id")
        boundary["runtime_mission_path"] = (mission or {}).get("_runtime_mission_path")
        return {
            "adapter": step.get("adapter"),
            "command": step.get("command"),
            "returncode": 0,
            "stdout": "MISSION_ORIGIN_BOUNDARY_PROBE\n",
            "stderr": "",
            "duration_s": 0.0,
            "qualification_intercept": True,
        }

    runtime.execute_step = intercepted_execute_step
    original_argv = list(sys.argv)
    try:
        sys.argv = [str(RUNTIME_DIR / "astra_runtime.py"), MISSION_REL]
        rc = runtime.main()
    finally:
        sys.argv = original_argv

    require(rc == 0, "CANONICAL_MAIN_NONZERO", rc)
    require(boundary == {
        "step_id": "mission-origin-boundary-probe",
        "mission_id": MISSION_ID,
        "runtime_mission_path": MISSION_REL,
    }, "BOUNDARY_IDENTITY_MISMATCH", boundary)

    state_path = runtime.STATE_DIR / (MISSION_ID + ".json")
    require(state_path.is_file(), "QUALIFICATION_STATE_MISSING")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    mission_sha256 = sha256_file(MISSION_PATH)
    require(state.get("status") == "COMPLETE", "QUALIFICATION_STATE_NOT_COMPLETE", state.get("status"))
    require(state.get("mission_path") == MISSION_REL, "STATE_MISSION_PATH_MISMATCH", state.get("mission_path"))
    require(state.get("mission_sha256") == mission_sha256, "STATE_MISSION_SHA256_MISMATCH", state.get("mission_sha256"))

    sys.path.insert(0, str(RUNTIME_DIR))
    validators = [
        ("apt", importlib.import_module("auto_apt_cli_acquisition"),
         ["APT_ORIGIN_MISSION_PATH_INVALID"], ["APT_ORIGIN_MISSION_MISSING"]),
        ("pypi", importlib.import_module("auto_pypi_library_acquisition"),
         ["PYPI_ORIGIN_MISSION_PATH_INVALID"], ["PYPI_ORIGIN_MISSION_MISSING"]),
        ("npm", importlib.import_module("auto_npm_library_acquisition"),
         ["NPM_ORIGIN_MISSION_PATH_INVALID"], ["NPM_ORIGIN_MISSION_MISSING"]),
        ("source", importlib.import_module("auto_python_source_codec_acquisition"),
         ["SOURCE_ORIGIN_MISSION_INVALID"], ["SOURCE_ORIGIN_MISSION_INVALID"]),
    ]

    validator_hashes = {}
    negative_controls = {}
    outside = "canonical/runtime/astra_runtime.py"
    missing = "canonical/astra_runtime/missions/__MISSION_ORIGIN_QUALIFICATION_MISSING__.json"
    for label, module, outside_prefixes, missing_prefixes in validators:
        fn = module._origin_mission_sha256
        observed = fn(ROOT, MISSION_REL)
        validator_hashes[label] = observed
        require(observed == mission_sha256, "VALIDATOR_MISSION_SHA256_MISMATCH", {
            "validator": label, "expected": mission_sha256, "observed": observed
        })
        negative_controls[label] = {
            "outside": expect_failure(lambda fn=fn: fn(ROOT, outside), outside_prefixes, label + ":outside"),
            "missing": expect_failure(lambda fn=fn: fn(ROOT, missing), missing_prefixes, label + ":missing"),
        }

    cleanup(runtime)

    report = {
        "schema": "PROJECT_BRAIN_CANONICAL_MISSION_ORIGIN_QUALIFICATION_V1",
        "status": "PASS",
        "route": "CANONICAL_ASTRA_RUNTIME_MISSION_ENTRYPOINT_TO_ACQUISITION_ORIGIN_IDENTITY",
        "brain_main": BRAIN_MAIN,
        "runner_main": RUNNER_MAIN,
        "mission_id": MISSION_ID,
        "mission_path": MISSION_REL,
        "mission_sha256": mission_sha256,
        "closure_blobs": observed_blobs,
        "boundary": boundary,
        "validator_hashes": validator_hashes,
        "negative_controls": negative_controls,
        "supplier_dispatch_executed": False,
        "network_supplier_discovery_executed": False,
        "parent_task_executed": False,
        "parent_capability_credit_authorized": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "runtime_mutated": False,
        "next_required_action": "FRESH_MATERIALLY_DIFFERENT_OPEN_ENDED_TASK_A_THROUGH_CANONICAL_MISSION_ENTRYPOINT",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
