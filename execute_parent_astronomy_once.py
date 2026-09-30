#!/usr/bin/env python3
import hashlib, importlib.util, json, math, pathlib, sys, traceback, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK_PATH=ROOT/"canonical/tasks/PARENT_ASTRONOMY_EROS_KEPLER_REAL_TASK_20260930_001.json"
TASK_BLOB="4cb0fbb4f46cf3c7302688197117cbaffe2d3943"
EXPECTED_RUNTIME_BLOBS={
  "canonical/runtime/astra_runtime.py":"85642a89a0d99c5e6cafa2e116ffdc24f04de32c",
  "canonical/runtime/goal_compiler.py":"b446257ca01ee858ada2fb52d0c7925f2ea4391f",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"b0fb5ccaf73552230dba24f914821d437b1a043d",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
}

def git_blob(path):
    raw=path.read_bytes()
    header=("blob "+str(len(raw))+"\0").encode()
    return hashlib.sha1(header+raw).hexdigest()

for rel,want in EXPECTED_RUNTIME_BLOBS.items():
    got=git_blob(ROOT/rel)
    if got!=want:
        raise SystemExit("RUNTIME_BLOB_MISMATCH:"+rel+":"+got)
if git_blob(TASK_PATH)!=TASK_BLOB:
    raise SystemExit("TASK_BLOB_MISMATCH:"+git_blob(TASK_PATH))

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
goal=task["goal_text"]
terminal={
  "schema":"PROJECT_BRAIN_PARENT_TASK_TERMINAL_V1",
  "task_id":task["task_id"],
  "task_git_blob":TASK_BLOB,
  "brain_base_commit":"43476b77a1314988183e3daed5f3f0d603f79877",
  "runtime_git_blobs":EXPECTED_RUNTIME_BLOBS,
  "goal":goal,
  "goal_sha256":hashlib.sha256(goal.encode()).hexdigest(),
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "execution_count":1,
  "source_task_replay":False,
}
try:
    spec=importlib.util.spec_from_file_location("parent_astronomy_brain_runtime",ROOT/"canonical/runtime/astra_runtime.py")
    runtime=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=runtime
    spec.loader.exec_module(runtime)
    mission={"mission_id":task["task_id"],"goal":goal}
    step={
      "adapter":"goal",
      "goal_ref":"goal",
      "verified_initial_facts":["network.http.available"],
      "max_controller_actions":16,
    }
    result=runtime.run_goal(step,mission)
    terminal["brain_result"]=result
    terminal["controller_mode"]=result.get("controller_mode")
    terminal["planner_model_last"]=result.get("planner_model_last")
    terminal["planning_mode"]=result.get("planning_mode")
    out=ROOT/task["required_output"]["output_path"]
    if (
      result.get("returncode")==0
      and result.get("controller_mode")=="MODEL_INDEPENDENT_ACTION_PLAN"
      and result.get("planner_model_last") is None
      and out.is_file()
    ):
        terminal["semantic_status"]="PASS"
        terminal["scientific_output"]=json.loads(out.read_text(encoding="utf-8"))
    else:
        terminal["semantic_status"]="FAIL"
        terminal["first_causal_gap"]="BRAIN_RETURNED_WITHOUT_REQUIRED_VERIFIED_SCIENTIFIC_OUTPUT"
except Exception as exc:
    terminal["semantic_status"]="FAIL"
    terminal["first_causal_gap"]=type(exc).__name__+":"+str(exc)
    terminal["exception_type"]=type(exc).__name__
    terminal["exception_message"]=str(exc)
    terminal["traceback"]=traceback.format_exc()

(ROOT/"PARENT_ASTRONOMY_TERMINAL.json").write_text(
    json.dumps(terminal,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print("PARENT_TASK_TERMINAL_EVIDENCE_PRESERVED")
print("semantic_status="+terminal["semantic_status"])
if terminal.get("first_causal_gap"):
    print("first_causal_gap="+terminal["first_causal_gap"])

oracle={
  "schema":"PROJECT_BRAIN_PARENT_ASTRONOMY_INDEPENDENT_ORACLE_V1",
  "source_task_replayed":False,
  "producer_runtime_imported":False,
}
if terminal["semantic_status"]!="PASS":
    oracle["status"]="NOT_RUN_DUE_TO_BRAIN_SEMANTIC_FAILURE"
    oracle["first_causal_gap"]=terminal.get("first_causal_gap")
else:
    url=task["source"]["url"]
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-Astronomy-Oracle/1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        raw=resp.read(1000000)
        assert resp.status==200
    payload=json.loads(raw.decode("utf-8"))
    elements=((payload.get("orbit") or {}).get("elements") or [])
    by_name={str(x.get("name")):x for x in elements if isinstance(x,dict)}
    a=float(by_name["a"]["value"])
    observed_period=float(by_name["per"]["value"])
    predicted=365.2568983*(a**1.5)
    delta=abs(predicted-observed_period)
    agreement=delta<=float(task["scientific_contract"]["max_abs_period_delta_days"])
    expected={
      "semimajor_axis_au":a,
      "jpl_period_days":observed_period,
      "predicted_period_days":predicted,
      "absolute_period_delta_days":delta,
      "agreement":agreement,
      "model_dependency_count":0,
    }
    observed=terminal["scientific_output"]
    def close(x,y,rel=1e-10,abs_tol=1e-10):
        return math.isclose(float(x),float(y),rel_tol=rel,abs_tol=abs_tol)
    checks={
      "semimajor_axis_au":close(observed["semimajor_axis_au"],a),
      "jpl_period_days":close(observed["jpl_period_days"],observed_period),
      "predicted_period_days":close(observed["predicted_period_days"],predicted,rel=1e-9),
      "absolute_period_delta_days":close(observed["absolute_period_delta_days"],delta,rel=1e-9),
      "agreement":observed["agreement"] is agreement,
      "model_dependency_count":observed["model_dependency_count"]==0,
    }
    oracle.update({
      "status":"PASS" if all(checks.values()) else "FAIL",
      "source_url":url,
      "source_body_sha256":hashlib.sha256(raw).hexdigest(),
      "expected":expected,
      "checks":checks,
      "model_dependency_count":0,
    })
(ROOT/"PARENT_ASTRONOMY_ORACLE.json").write_text(
    json.dumps(oracle,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print("PARENT_ASTRONOMY_ORACLE_STATUS="+oracle["status"])
