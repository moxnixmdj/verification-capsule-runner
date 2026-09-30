#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
MISSION_REL="canonical/astra_runtime/missions/MISSION_IDENTITY_AUTO_ACQUISITION_CANARY_20260930_V1.json"
MISSION_PATH=ROOT/MISSION_REL
MISSION_ID="MISSION-IDENTITY-AUTO-ACQUISITION-CANARY-20260930-V1"
REPORT=ROOT/"runtime-mission-identity-canary-report.json"
EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
  "canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def emit(payload):
    REPORT.write_text(json.dumps(payload,indent=2,sort_keys=True,default=str)+"\\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True,default=str),flush=True)

closure={}
for rel,expected in EXPECTED_BLOBS.items():
    path=ROOT/rel
    observed=git_blob_sha(path) if path.is_file() else None
    closure[rel]={"expected":expected,"observed":observed,"match":observed==expected}
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_RUNTIME_MISSION_IDENTITY_CANARY_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "failed_path":rel,
          "closure":closure,
          "parent_task_executed":False,
          "capability_credit":False,
          "incremental_spend_usd":0
        })
        raise SystemExit(1)

if not MISSION_PATH.is_file():
    emit({
      "schema":"PROJECT_BRAIN_RUNTIME_MISSION_IDENTITY_CANARY_V1",
      "status":"MISSION_FILE_MISSING",
      "mission_path":MISSION_REL,
      "parent_task_executed":False,
      "capability_credit":False,
      "incremental_spend_usd":0
    })
    raise SystemExit(2)

mission=json.loads(MISSION_PATH.read_text(encoding="utf-8"))
if mission.get("mission_id")!=MISSION_ID:
    raise SystemExit("MISSION_ID_MISMATCH")
if (mission.get("constraints") or {}).get("parent_task") is not False:
    raise SystemExit("CANARY_MUST_BE_NON_PARENT")
if (mission.get("constraints") or {}).get("capability_credit") is not False:
    raise SystemExit("CANARY_MUST_HAVE_ZERO_CAPABILITY_CREDIT")
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    raise SystemExit("MODEL_PLANNER_DISABLE_ENV_REQUIRED")

expected_mission_sha=sha256(MISSION_PATH)
registry_path=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
registry_before=sha256(registry_path)

sys.path.insert(0,str(RUNTIME))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("brain_runtime_mission_identity_canary",RUNTIME/"astra_runtime.py")
apt=load("brain_canary_auto_apt",RUNTIME/"auto_apt_cli_acquisition.py")
pypi=load("brain_canary_auto_pypi",RUNTIME/"auto_pypi_library_acquisition.py")

dispatch_calls=[]

class CanaryAuto:
    @staticmethod
    def dispatch(goal, mission_id, mission_path, root, discovery=None):
        if mission_id!=MISSION_ID:
            raise RuntimeError("CANARY_MISSION_ID_NOT_PROPAGATED:"+str(mission_id))
        if mission_path!=MISSION_REL:
            raise RuntimeError("CANARY_MISSION_PATH_NOT_PROPAGATED:"+str(mission_path))
        apt_sha=apt._origin_mission_sha256(root,mission_path)
        pypi_sha=pypi._origin_mission_sha256(root,mission_path)
        if apt_sha!=expected_mission_sha:
            raise RuntimeError("APT_MISSION_SHA_MISMATCH:"+str(apt_sha))
        if pypi_sha!=expected_mission_sha:
            raise RuntimeError("PYPI_MISSION_SHA_MISMATCH:"+str(pypi_sha))
        dispatch_calls.append({
          "mission_id":mission_id,
          "mission_path":mission_path,
          "apt_origin_mission_sha256":apt_sha,
          "pypi_origin_mission_sha256":pypi_sha,
          "discovery_supplied":discovery is not None
        })
        raise RuntimeError("MISSION_IDENTITY_CANARY_PASSED_GUARDS")

class FakeDiscovery:
    @staticmethod
    def search_all(goal,limit_per_source=30):
        return {
          "schema":"PROJECT_BRAIN_CANARY_FAKE_DISCOVERY_V1",
          "query":goal,
          "candidates":[],
          "canary_only":True
        }

runtime._load_auto_capability_acquisition=lambda: CanaryAuto
runtime._load_capability_discovery=lambda: FakeDiscovery

argv_before=list(sys.argv)
try:
    sys.argv=[str(RUNTIME/"astra_runtime.py"),MISSION_REL]
    rc=runtime.main()
finally:
    sys.argv=argv_before

state_path=ROOT/"canonical/astra_runtime/state"/(MISSION_ID+".json")
state=json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
registry_after=sha256(registry_path)
blocker=state.get("blocker") or {}
blocker_text=json.dumps(blocker,sort_keys=True)

checks={
  "runtime_main_returned_blocked_after_canary":rc==3,
  "state_exists":state_path.is_file(),
  "state_mission_path_exact":state.get("mission_path")==MISSION_REL,
  "state_mission_sha256_exact":state.get("mission_sha256")==expected_mission_sha,
  "state_status_blocked":state.get("status")=="BLOCKED",
  "later_acquisition_blocker_observed":"CAPABILITY_ACQUISITION_REQUIRED" in blocker_text,
  "apt_invalid_absent":"APT_ORIGIN_MISSION_PATH_INVALID" not in blocker_text,
  "pypi_invalid_absent":"PYPI_ORIGIN_MISSION_PATH_INVALID" not in blocker_text,
  "real_origin_guards_called":len(dispatch_calls)>=2,
  "all_guard_hashes_exact":bool(dispatch_calls) and all(
      x["apt_origin_mission_sha256"]==expected_mission_sha
      and x["pypi_origin_mission_sha256"]==expected_mission_sha
      and x["mission_path"]==MISSION_REL
      for x in dispatch_calls
  ),
  "registry_unchanged":registry_before==registry_after,
}
status="PASS" if all(checks.values()) else "FAIL"
report={
  "schema":"PROJECT_BRAIN_RUNTIME_MISSION_IDENTITY_CANARY_V1",
  "status":status,
  "purpose":"Validate canonical astra_runtime.main mission identity propagation into autonomous acquisition without a parent task or registry mutation.",
  "mission_id":MISSION_ID,
  "mission_path":MISSION_REL,
  "mission_sha256":expected_mission_sha,
  "runtime_main_returncode":rc,
  "checks":checks,
  "dispatch_calls":dispatch_calls,
  "terminal_blocker":blocker,
  "closure":closure,
  "registry_sha256_before":registry_before,
  "registry_sha256_after":registry_after,
  "parent_task_executed":False,
  "model_planner_disabled":True,
  "model_dependency_count":0,
  "capability_credit":False,
  "incremental_spend_usd":0,
  "supplier_discovery_stubbed_after_acquisition_boundary":True,
  "runtime_code_mutated":False,
}
emit(report)
raise SystemExit(0 if status=="PASS" else 3)
