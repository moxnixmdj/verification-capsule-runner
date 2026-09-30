#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK_PATH=ROOT/"canonical/tasks/PARENT_ASTRONOMY_EROS_KEPLER_REAL_TASK_20260930_001.json"
REPORT_PATH=ROOT/"parent-astronomy-eros-kepler-report.json"

EXPECTED_GIT_BLOBS={
  "canonical/runtime/goal_compiler.py":"b446257ca01ee858ada2fb52d0c7925f2ea4391f",
  "canonical/runtime/astra_runtime.py":"85642a89a0d99c5e6cafa2e116ffdc24f04de32c",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"b0fb5ccaf73552230dba24f914821d437b1a043d",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/tasks/PARENT_ASTRONOMY_EROS_KEPLER_REAL_TASK_20260930_001.json":"4cb0fbb4f46cf3c7302688197117cbaffe2d3943",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def write_report(report):
    REPORT_PATH.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

for rel,expected in EXPECTED_GIT_BLOBS.items():
    p=ROOT/rel
    if not p.is_file():
        write_report({"schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_EXECUTION_V1","status":"CARRIER_CLOSURE_FAIL","missing":rel})
        raise SystemExit(1)
    got=git_blob_sha(p)
    if got!=expected:
        write_report({"schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_EXECUTION_V1","status":"CARRIER_BLOB_MISMATCH","path":rel,"expected":expected,"observed":got})
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!="PARENT-ASTRONOMY-EROS-KEPLER-REAL-TASK-20260930-001":
    raise SystemExit("TASK_ID_MISMATCH")
if task.get("execution_constraints",{}).get("exactly_one_execution") is not True:
    raise SystemExit("ONE_SHOT_CONTRACT_MISSING")
if task.get("execution_constraints",{}).get("model_dependency_count")!=0:
    raise SystemExit("MODEL_DEPENDENCY_CONTRACT_INVALID")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("parent_astronomy_candidate_astra_runtime",ROOT/"canonical/runtime/astra_runtime.py")
goal=str(task["goal_text"])
mission={
  "mission_id":"PARENT-ASTRONOMY-EROS-KEPLER-REAL-TASK-20260930-001",
  "goal":goal,
}
step={
  "id":"parent_astronomy_eros_kepler",
  "goal_ref":"goal",
  "allow_optional_model_planner":False,
}

report={
  "schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_EXECUTION_V1",
  "task_id":task["task_id"],
  "domain":task["domain"],
  "source_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "canonical_brain_base":"43476b77a1314988183e3daed5f3f0d603f79877",
  "task_git_blob":EXPECTED_GIT_BLOBS[str(TASK_PATH.relative_to(ROOT))],
  "runtime_blobs":{k:v for k,v in EXPECTED_GIT_BLOBS.items() if k!=str(TASK_PATH.relative_to(ROOT))},
}

try:
    result=runtime.run_goal(step,mission)
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "first_causal_blocker":type(exc).__name__+":"+str(exc),
      "parent_task_completed":False,
      "independent_oracle_executed":False,
    })
    write_report(report)
    raise SystemExit(2)

output_rel=task["required_output"]["output_path"]
output_path=ROOT/output_rel
if not output_path.is_file():
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "first_causal_blocker":"REQUIRED_PARENT_RESULT_ARTIFACT_MISSING_AFTER_RUNTIME_SUCCESS",
      "runtime_result":result,
      "parent_task_completed":False,
      "independent_oracle_executed":False,
    })
    write_report(report)
    raise SystemExit(3)

try:
    producer=json.loads(output_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "first_causal_blocker":"PARENT_RESULT_JSON_INVALID:"+type(exc).__name__,
      "parent_task_completed":False,
      "independent_oracle_executed":False,
    })
    write_report(report)
    raise SystemExit(4)

url=task["source"]["url"]
req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-Astronomy-Oracle/1"})
with urllib.request.urlopen(req,timeout=20) as resp:
    payload=json.loads(resp.read(2000000).decode("utf-8"))

elements=payload["orbit"]["elements"]
by_name={str(x.get("name")):x for x in elements if isinstance(x,dict)}
a=float(by_name["a"]["value"])
period=float(by_name["per"]["value"])
pred=365.2568983*(a**1.5)
delta=abs(pred-period)
agreement=delta<=2.0
object_name=str((payload.get("object") or {}).get("fullname") or (payload.get("object") or {}).get("shortname") or "")

failures=[]
def close(x,y,tol=1e-10):
    return math.isclose(float(x),float(y),rel_tol=tol,abs_tol=tol)

if not close(producer.get("semimajor_axis_au"),a): failures.append("SEMIMAJOR_AXIS_MISMATCH")
if not close(producer.get("jpl_period_days"),period): failures.append("JPL_PERIOD_MISMATCH")
if not close(producer.get("predicted_period_days"),pred): failures.append("PREDICTED_PERIOD_MISMATCH")
if not close(producer.get("absolute_period_delta_days"),delta): failures.append("DELTA_MISMATCH")
if bool(producer.get("agreement"))!=agreement: failures.append("AGREEMENT_MISMATCH")
if int(producer.get("model_dependency_count",-1))!=0: failures.append("MODEL_DEPENDENCY_COUNT_MISMATCH")
if str(producer.get("source_url") or "")!=url: failures.append("SOURCE_URL_MISMATCH")

report.update({
  "status":"PASS" if not failures else "FAIL_INDEPENDENT_ORACLE",
  "parent_task_completed":not failures,
  "runtime_result":result,
  "producer":producer,
  "independent_oracle":{
    "method":"fresh exact JPL refetch; extract orbital elements by element name; independent Python math",
    "producer_modules_imported":False,
    "object":object_name,
    "semimajor_axis_au":a,
    "jpl_period_days":period,
    "predicted_period_days":pred,
    "absolute_period_delta_days":delta,
    "agreement":agreement,
  },
  "failures":failures,
  "independent_oracle_executed":True,
})
write_report(report)
if failures:
    raise SystemExit(5)
