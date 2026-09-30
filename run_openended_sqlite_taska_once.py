#!/usr/bin/env python3
import hashlib, importlib.util, json, os, pathlib, sys, traceback

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_REL="canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
TASK_PATH=ROOT/TASK_REL
REPORT=ROOT/"openended-sqlite-taska-terminal.json"
BRAIN_BASE="797d5fbea5f230a31044006755beb98ae387134b"
BRAIN_PR=338
TASK_BLOB="5d09c9eebcb09612525836e7926bdf297f4bad32"
TASK_ID="PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
EXPECTED_RUNTIME_BLOBS={
 "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
 "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
 "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
 "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
 "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
 "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
 "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
 "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True,default=str))

closure={}
all_expected={TASK_REL:TASK_BLOB,**EXPECTED_RUNTIME_BLOBS}
for rel,expected in all_expected.items():
    p=ROOT/rel
    got=git_blob_sha(p) if p.is_file() else None
    closure[rel]={"expected":expected,"observed":got,"match":got==expected}
if not all(x["match"] for x in closure.values()):
    emit({
      "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
      "status":"CARRIER_CLOSURE_FAIL","brain_base":BRAIN_BASE,"brain_pr":BRAIN_PR,
      "task_id":TASK_ID,"task_executed":False,"execution_count":0,
      "closure":closure,"incremental_spend_usd":0
    })
    raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
anti=task.get("anti_leakage") or {}
if any(bool(v) for v in anti.values()):
    raise SystemExit("TASK_ANTI_LEAKAGE_CONTRACT_VIOLATED")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True:
    raise SystemExit("EXACTLY_ONE_EXECUTION_REQUIRED")
if constraints.get("model_dependency_count")!=0:
    raise SystemExit("ZERO_MODEL_DEPENDENCY_REQUIRED")
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    raise SystemExit("MODEL_PLANNER_DISABLE_ENV_REQUIRED")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load("openended_taska_runtime",RUNTIME/"astra_runtime.py")
mission={
  "mission_id":TASK_ID,
  "goal":task["goal_text"],
}
step={
  "id":"openended_parent_task_a",
  "adapter":"goal",
  "goal_ref":"goal",
  "allow_optional_model_planner":False,
  "max_cycles":8,
}
report={
  "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
  "brain_base":BRAIN_BASE,"brain_pr":BRAIN_PR,"task_id":TASK_ID,
  "task_blob":TASK_BLOB,"closure":closure,
  "task_executed":True,"execution_count":1,"source_task_replay":False,
  "incremental_spend_usd":0,"model_planner_disabled":True,
}
try:
    result=runtime.run_goal(step,mission)
except Exception as exc:
    evidence=[]
    evid_dir=ROOT/"canonical"/"astra_runtime"/"evidence"
    if evid_dir.is_dir():
        for p in sorted(evid_dir.glob(TASK_ID+"*")):
            if p.is_file():
                try:
                    raw=p.read_text(encoding="utf-8",errors="replace")
                except Exception:
                    raw=""
                evidence.append({
                  "path":str(p.relative_to(ROOT)),
                  "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                  "content_excerpt":raw[:12000],
                })
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "exception_type":type(exc).__name__,
      "first_causal_blocker":str(exc),
      "traceback_excerpt":traceback.format_exc()[-12000:],
      "evidence":evidence,
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(2)

report["producer_result"]=result
report["producer_returncode"]=result.get("returncode") if isinstance(result,dict) else None
report["model_dependency_count"]=result.get("model_dependency_count") if isinstance(result,dict) else None
report["cognition_dependency_class"]=result.get("cognition_dependency_class") if isinstance(result,dict) else None
report["cognition_provenance_authority"]=result.get("cognition_provenance_authority") if isinstance(result,dict) else None
prov_ok=(
    isinstance(result,dict)
    and result.get("model_dependency_count")==0
    and result.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
    and result.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
)
report["status"]="PRODUCER_RETURNED__PENDING_INDEPENDENT_ORACLE" if prov_ok else "FAIL_COGNITION_PROVENANCE"
report["parent_task_completed"]=False
report["independent_oracle_executed"]=False
emit(report)
if not prov_ok:
    raise SystemExit(3)
