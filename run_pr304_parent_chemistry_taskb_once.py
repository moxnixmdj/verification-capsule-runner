#!/usr/bin/env python3
import hashlib, importlib.util, json, math, pathlib, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
TASK_PATH=ROOT/"canonical/tasks/PARENT_CHEMISTRY_AMMONIUM_CHLORIDE_MASS_BALANCE_REAL_TASK_20260930_001.json"
REPORT=ROOT/"pr304-parent-chemistry-taskb-report.json"
EXPECTED_BLOBS={
  "canonical/runtime/astra_runtime.py":"85642a89a0d99c5e6cafa2e116ffdc24f04de32c",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py":"443e3386f11156e55635556b6e8f8ad7d7733592",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
  "canonical/tasks/PARENT_CHEMISTRY_AMMONIUM_CHLORIDE_MASS_BALANCE_REAL_TASK_20260930_001.json":"d423431ec9770283e62dfa590fe3f45c623f3f53",
}
BRAIN_BASE="5262fd6e0d132ff8a2ac30f43f5b79ff3efd4142"
BRAIN_PR=304
TASK_ID="PARENT-CHEMISTRY-AMMONIUM-CHLORIDE-MASS-BALANCE-REAL-TASK-20260930-001"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed!=expected:
        emit({"schema":"PROJECT_BRAIN_PARENT_TASK_B_CHEMISTRY_TERMINAL_V1","status":"CARRIER_CLOSURE_FAIL","path":rel,"expected_blob":expected,"observed_blob":observed,"brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,"task_executed":False})
        raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True or constraints.get("model_dependency_count")!=0:
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

compiler=load("pr304_goal_compiler",RUNTIME/"goal_compiler.py")
runtime=load("pr304_astra_runtime",RUNTIME/"astra_runtime.py")
registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]
report={"schema":"PROJECT_BRAIN_PARENT_TASK_B_CHEMISTRY_TERMINAL_V1","status":"STARTED","brain_pr":BRAIN_PR,"brain_base":BRAIN_BASE,"task_id":TASK_ID,"domain":task.get("domain"),"task_blob":EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],"runtime_blobs":{k:v for k,v in EXPECTED_BLOBS.items() if k!=str(TASK_PATH.relative_to(ROOT))},"source_task_replay":False,"execution_count":1,"model_dependency_count":0,"incremental_spend_usd":0}
goal=str(task["goal_text"])
try:
    compiled=compiler.compile_goal(goal,registry,ROOT)
except Exception as exc:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","task_executed":True,"parent_task_completed":False,"first_causal_blocker":"COMPILE:"+type(exc).__name__+":"+str(exc),"independent_oracle_executed":False}); emit(report); raise SystemExit(2)

expression_parts=[p for p in compiled.get("compiled_parts",[]) if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"]
relation_parts=[p for p in compiled.get("compiled_parts",[]) if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"]
if len(expression_parts)!=1 or len(relation_parts)!=1:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","task_executed":True,"parent_task_completed":False,"first_causal_blocker":"COMPILED_PARENT_CHAIN_SHAPE_INVALID","expression_part_count":len(expression_parts),"relation_part_count":len(relation_parts),"independent_oracle_executed":False}); emit(report); raise SystemExit(3)
expr=expression_parts[0]; rel=relation_parts[0]
report["compiled_route"]={"clause_coverage_verified":compiled.get("clause_coverage_verified"),"numeric_expression_capability":expr.get("selected_capability"),"numeric_expression_variable_bindings":expr.get("variable_bindings"),"numeric_relation_capability":rel.get("selected_capability"),"relation_producer_result_cycles":rel.get("producer_result_cycles")}
mission={"mission_id":TASK_ID,"goal":goal}
step={"id":"parent_task_b_chemistry","controller_actions":compiled["controller_actions"],"max_controller_actions":32}
try:
    run=runtime._run_model_independent_goal(step,mission,goal)
except Exception as exc:
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","task_executed":True,"parent_task_completed":False,"first_causal_blocker":"EXECUTE:"+type(exc).__name__+":"+str(exc),"independent_oracle_executed":False}); emit(report); raise SystemExit(4)

result_path=ROOT/str(rel.get("output_path") or "")
if not result_path.is_file():
    report.update({"status":"FAIL_FIRST_CAUSAL_GAP","task_executed":True,"parent_task_completed":False,"first_causal_blocker":"FINAL_RELATION_ARTIFACT_MISSING","runtime_result":run,"independent_oracle_executed":False}); emit(report); raise SystemExit(5)
producer=json.loads(result_path.read_text(encoding="utf-8"))

def resolve(payload,path):
    cur=payload
    for part in path: cur=cur[part]
    return cur
def fetch_value(src):
    req=urllib.request.Request(src["url"],headers={"User-Agent":"ProjectBrain-Independent-Chemistry-TaskB-Oracle/1"})
    with urllib.request.urlopen(req,timeout=20) as resp: payload=json.loads(resp.read(1000000).decode("utf-8"))
    return float(resolve(payload,src["json_path"]))

src=task["sources"]
ammonia=fetch_value(src["ammonia"])
hcl=fetch_value(src["hydrogen_chloride"])
official=fetch_value(src["ammonium_chloride"])
predicted=ammonia+hcl
delta=abs(predicted-official)
threshold=float(task["scientific_contract"]["comparison_threshold_g_mol"])
predicate=delta<=threshold
failures=[]
def close(a,b,tol=1e-10):
    try:return math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol)
    except Exception:return False
if not close(producer.get("left"),predicted): failures.append("LEFT_PREDICTED_MW_MISMATCH")
if not close(producer.get("right"),official): failures.append("RIGHT_OFFICIAL_MW_MISMATCH")
if not close(producer.get("threshold"),threshold): failures.append("THRESHOLD_MISMATCH")
if not close(producer.get("absolute_difference"),delta): failures.append("ABSOLUTE_DIFFERENCE_MISMATCH")
if producer.get("relation")!="ABS_DIFF_LTE": failures.append("RELATION_MISMATCH")
if producer.get("predicate") is not predicate: failures.append("PREDICATE_MISMATCH")
report.update({"status":"PASS" if not failures else "FAIL_INDEPENDENT_ORACLE","task_executed":True,"parent_task_completed":not failures,"runtime_result":run,"producer_relation":producer,"independent_oracle":{"method":"fresh direct PubChem refetch plus independent Python molecular-weight mass-balance recomputation","producer_modules_imported":False,"ammonia_mw":ammonia,"hydrogen_chloride_mw":hcl,"official_ammonium_chloride_mw":official,"predicted_product_mw":predicted,"absolute_difference":delta,"threshold":threshold,"predicate":predicate},"independent_oracle_executed":True,"failures":failures})
emit(report)
if failures: raise SystemExit(6)
