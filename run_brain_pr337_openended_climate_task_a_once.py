#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_PATH=ROOT/"canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT=ROOT/"brain-pr337-open-ended-climate-task-a-terminal.json"
BRAIN_BASE="797d5fbea5f230a31044006755beb98ae387134b"
BRAIN_PR=337
TASK_ID="PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"
EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
  "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json":"6f0e889e23cfba6c511b3a54cb86acba48bc9d3a",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def snapshot():
    out={}
    for relroot in ("canonical/astra_runtime/state","canonical/astra_runtime/evidence","canonical/astra_runtime/tmp"):
        root=ROOT/relroot
        if not root.exists(): continue
        for p in root.rglob("*"):
            if p.is_file():
                try: out[str(p.relative_to(ROOT))]=sha256(p)
                except Exception: pass
    return out

def capture_changed(before):
    after=snapshot()
    changed={}
    for rel,digest in after.items():
        if before.get(rel)==digest: continue
        p=ROOT/rel
        rec={"sha256":digest,"size":p.stat().st_size}
        if p.stat().st_size<=250000:
            try: rec["content_text"]=p.read_text(encoding="utf-8")
            except Exception: pass
        changed[rel]=rec
    return changed

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+ "\\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({
          "schema":"PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_TERMINAL_V1",
          "status":"CARRIER_CLOSURE_FAIL",
          "brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,
          "task_id":TASK_ID,"task_executed":False,"execution_count":0,
          "path":rel,"expected_blob":expected,"observed_blob":observed
        })
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID: raise SystemExit("TASK_ID_MISMATCH")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")
anti=task.get("anti_leakage") or {}
if any(anti.get(k) is not False for k in (
    "authority_name_preprovided","authority_domain_preprovided","source_url_preprovided",
    "dataset_identifier_preprovided","json_or_table_path_preprovided",
    "quantitative_formula_preprovided","controller_action_graph_preprovided",
    "expected_answer_precommitted")):
    raise SystemExit("OPEN_ENDED_ANTI_LEAKAGE_CONTRACT_INVALID")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("brain_pr337_astra_runtime",RUNTIME/"astra_runtime.py")
goal=str(task["goal_text"])
mission={"mission_id":TASK_ID,"goal":goal}
step={
  "id":"parent_open_ended_climate_task_a",
  "goal_ref":"goal",
  "allow_optional_model_planner":False
}
before=snapshot()
report={
  "schema":"PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_TERMINAL_V1",
  "status":"STARTED",
  "brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,"task_id":TASK_ID,
  "task_blob":EXPECTED_BLOBS["canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"],
  "runtime_blobs":{k:v for k,v in EXPECTED_BLOBS.items() if k!="canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"},
  "source_task_replay":False,"task_executed":True,"execution_count":1,
  "incremental_spend_usd":0,"independent_oracle_executed":False
}
try:
    result=runtime.run_goal(step,mission)
except Exception as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "producer_terminal_success":False,
      "parent_task_completed":False,
      "first_causal_blocker":"EXECUTE:"+type(exc).__name__+":"+str(exc),
      "changed_runtime_artifacts":capture_changed(before)
    })
    emit(report)
    raise SystemExit(2)

changed=capture_changed(before)
report["runtime_result"]=result
report["changed_runtime_artifacts"]=changed
authority=result.get("cognition_provenance_authority") if isinstance(result,dict) else None
count=result.get("model_dependency_count") if isinstance(result,dict) else None
klass=result.get("cognition_dependency_class") if isinstance(result,dict) else None
if authority!="ASTRA_RUNTIME_DERIVED_V1" or count!=0 or klass!="MODEL_INDEPENDENT":
    report.update({
      "status":"FAIL_COGNITION_PROVENANCE",
      "producer_terminal_success":False,
      "parent_task_completed":False,
      "first_causal_blocker":"RUNTIME_DERIVED_ZERO_MODEL_PROVENANCE_REQUIRED",
      "observed_cognition_provenance_authority":authority,
      "observed_model_dependency_count":count,
      "observed_cognition_dependency_class":klass
    })
    emit(report)
    raise SystemExit(3)

report.update({
  "status":"PRODUCER_TERMINATED_SUCCESS_PENDING_INDEPENDENT_ORACLE",
  "producer_terminal_success":True,
  "parent_task_completed":False,
  "model_dependency_count":count,
  "cognition_dependency_class":klass,
  "cognition_provenance_authority":authority,
  "next_required_action":"INDEPENDENTLY_VERIFY_PRODUCER_CITED_PRIMARY_EVIDENCE_AND_CONSEQUENTIAL_CALCULATIONS_WITHOUT_REEXECUTING_PRODUCER"
})
emit(report)
