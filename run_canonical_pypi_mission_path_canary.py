#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parent
MISSION_REL="canonical/astra_runtime/missions/ASTRA_RUNTIME_MISSION_PATH_PYPI_CANARY_CBOR_001.json"
MISSION_ID="ASTRA-RUNTIME-MISSION-PATH-PYPI-CANARY-CBOR-001"
REPORT=ROOT/"canonical-pypi-mission-path-canary-report.json"

EXPECTED_BLOBS={
  "canonical/astra_runtime/missions/ASTRA_RUNTIME_MISSION_PATH_PYPI_CANARY_CBOR_001.json":"b30da3f48e52c0525432fa9da19c83f084eacb66",
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
  "canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py":"443e3386f11156e55635556b6e8f8ad7d7733592"
}

def emit(payload):
    REPORT.write_text(json.dumps(payload,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True,default=str),flush=True)

def git_blob(path):
    proc=subprocess.run(
        ["git","hash-object",path],
        cwd=ROOT,text=True,capture_output=True,timeout=20
    )
    if proc.returncode!=0:
        return None
    return proc.stdout.strip()

closure={}
for rel,expected in EXPECTED_BLOBS.items():
    observed=git_blob(rel)
    closure[rel]={"expected":expected,"observed":observed,"match":observed==expected}
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_CANONICAL_PYPI_MISSION_PATH_CANARY_CARRIER_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "failed_path":rel,
          "closure":closure,
          "canonical_brain_base":"f94650b3727a6e35774b465312bbedc295cded2c",
          "parent_task_executed":False,
          "parent_capability_credit":False,
          "incremental_spend_usd":0
        })
        raise SystemExit(1)

mission_path=ROOT/MISSION_REL
mission_sha256=hashlib.sha256(mission_path.read_bytes()).hexdigest()
mission=json.loads(mission_path.read_text(encoding="utf-8"))
if mission.get("mission_id")!=MISSION_ID:
    raise SystemExit("MISSION_ID_MISMATCH")
constraints=mission.get("constraints") or {}
if constraints.get("non_parent_canary") is not True:
    raise SystemExit("NON_PARENT_CANARY_REQUIRED")
if constraints.get("parent_capability_credit") is not False:
    raise SystemExit("ZERO_PARENT_CAPABILITY_CREDIT_REQUIRED")

env=os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"]="1"
proc=subprocess.run(
    [sys.executable,"canonical/runtime/astra_runtime.py",MISSION_REL],
    cwd=ROOT,text=True,capture_output=True,timeout=600,env=env
)

state_path=ROOT/"canonical/astra_runtime/state"/(MISSION_ID+".json")
state={}
if state_path.is_file():
    try:
        state=json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        state={"_parse_error":True}

evidence_dir=ROOT/"canonical/astra_runtime/evidence"
evidence_records=[]
if evidence_dir.is_dir():
    for path in sorted(evidence_dir.glob(MISSION_ID+"*")):
        item={
          "path":str(path.relative_to(ROOT)),
          "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
          "bytes":path.stat().st_size
        }
        if path.suffix.lower()==".json" and path.stat().st_size<=400000:
            try:
                item["json"]=json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        evidence_records.append(item)

combined=(proc.stdout or "")+"\n"+(proc.stderr or "")+"\n"+json.dumps(state,sort_keys=True)+"\n"+json.dumps(evidence_records,sort_keys=True)
forbidden=[
  "APT_ORIGIN_MISSION_PATH_INVALID",
  "PYPI_ORIGIN_MISSION_PATH_INVALID"
]
forbidden_hits=[x for x in forbidden if x in combined]

status="PASS" if (
    proc.returncode==0
    and state.get("status")=="COMPLETE"
    and state.get("mission_path")==MISSION_REL
    and state.get("mission_sha256")==mission_sha256
    and not forbidden_hits
) else "FAIL"

git_status=subprocess.run(
    ["git","status","--porcelain=v1"],
    cwd=ROOT,text=True,capture_output=True,timeout=20
).stdout.splitlines()

report={
  "schema":"PROJECT_BRAIN_CANONICAL_PYPI_MISSION_PATH_CANARY_CARRIER_V1",
  "status":status,
  "canonical_brain_base":"f94650b3727a6e35774b465312bbedc295cded2c",
  "canonical_mission_blob":"b30da3f48e52c0525432fa9da19c83f084eacb66",
  "mission_id":MISSION_ID,
  "mission_path":MISSION_REL,
  "mission_sha256":mission_sha256,
  "runtime_returncode":proc.returncode,
  "runtime_stdout_tail":(proc.stdout or "")[-12000:],
  "runtime_stderr_tail":(proc.stderr or "")[-12000:],
  "runtime_state":state,
  "evidence_records":evidence_records,
  "forbidden_terminal_causes":forbidden,
  "forbidden_hits":forbidden_hits,
  "git_status_after_execution":git_status,
  "closure":closure,
  "parent_task_executed":False,
  "parent_capability_credit":False,
  "model_planner_disabled":True,
  "model_dependency_count":0,
  "incremental_spend_usd":0
}
emit(report)
raise SystemExit(0 if status=="PASS" else 2)
