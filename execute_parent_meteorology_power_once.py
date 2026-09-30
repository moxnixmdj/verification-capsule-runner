#!/usr/bin/env python3
import hashlib, importlib.util, json, math, pathlib, sys, traceback, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK_PATH=ROOT/"canonical/tasks/PARENT_METEOROLOGY_NASA_POWER_DAILY_MEAN_REAL_TASK_20260930_001.json"
BRAIN_BASE="144a1baadbb927645b1e183a85e4675f5cf44f1f"
TASK_BLOB="8fbe0b739a796733d20368cc629247379d133765"
EXPECTED_RUNTIME_BLOBS={
  "canonical/runtime/astra_runtime.py":"85642a89a0d99c5e6cafa2e116ffdc24f04de32c",
  "canonical/runtime/goal_compiler.py":"f1c72b7a1d2aebf146d2702a49e425605fa17217",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"23f7b79fca15593eb563bdcdba17c8b972f006db",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py":"443e3386f11156e55635556b6e8f8ad7d7733592",
  "canonical/runtime/bound_capabilities/jq_query.py":"f0b644274c1ffbff7ea5adb81e07e00435d2ac4c",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
}

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()

for rel,want in EXPECTED_RUNTIME_BLOBS.items():
    got=git_blob(ROOT/rel)
    if got!=want:
        raise SystemExit("RUNTIME_BLOB_MISMATCH:"+rel+":"+got)
if git_blob(TASK_PATH)!=TASK_BLOB:
    raise SystemExit("TASK_BLOB_MISMATCH:"+git_blob(TASK_PATH))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
goal=task["goal_text"]
compiler=load("parent_meteorology_goal_compiler",ROOT/"canonical/runtime/goal_compiler.py")
runtime=load("parent_meteorology_brain_runtime",ROOT/"canonical/runtime/astra_runtime.py")
registry=json.loads((ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]

terminal={
  "schema":"PROJECT_BRAIN_PARENT_METEOROLOGY_TERMINAL_V1",
  "task_id":task["task_id"],
  "task_git_blob":TASK_BLOB,
  "brain_base_commit":BRAIN_BASE,
  "runtime_git_blobs":EXPECTED_RUNTIME_BLOBS,
  "goal_sha256":hashlib.sha256(goal.encode()).hexdigest(),
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "execution_count":1,
  "source_task_replay":False,
}
try:
    compiled=compiler.compile_goal(goal,registry,ROOT)
    terminal["compiler_clause_coverage_verified"]=bool(compiled.get("clause_coverage_verified"))
    parts=compiled.get("compiled_parts") or []
    sources=[p for p in parts if p.get("mode")=="AUTHORITATIVE_JSON_KNOWLEDGE_FETCH"]
    exprs=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"]
    relations=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"]
    if len(sources)!=3 or len(exprs)!=1 or len(relations)!=1:
        raise RuntimeError("COMPILED_CAUSAL_SHAPE_INVALID:"+json.dumps({"sources":len(sources),"exprs":len(exprs),"relations":len(relations)}))
    expr=exprs[0]; relation=relations[0]
    by_parameter={}
    for p in sources:
        jp=p.get("json_path") or []
        if len(jp)<3:
            raise RuntimeError("SOURCE_PATH_SHAPE_INVALID")
        by_parameter[str(jp[2])]=p
    if set(by_parameter)!={"T2M_MAX","T2M_MIN","T2M"}:
        raise RuntimeError("SOURCE_PARAMETER_SET_INVALID:"+repr(sorted(by_parameter)))
    expected_relation_cycles=[int(expr["result_cycle"]),int(by_parameter["T2M"]["result_cycle"])]
    if [int(x) for x in relation.get("producer_result_cycles") or []]!=expected_relation_cycles:
        raise RuntimeError("RELATION_CAUSAL_BINDING_INVALID:"+repr(relation.get("producer_result_cycles")))

    mission={"mission_id":task["task_id"],"goal":goal}
    step={"adapter":"goal","goal_ref":"goal","verified_initial_facts":["network.http.available"],"max_controller_actions":20}
    result=runtime.run_goal(step,mission)
    terminal["brain_result"]=result
    terminal["controller_mode"]=result.get("controller_mode")
    terminal["planner_model_last"]=result.get("planner_model_last")
    terminal["planning_mode"]=result.get("planning_mode")

    required=[
      by_parameter["T2M_MAX"]["evidence_path"],
      by_parameter["T2M_MIN"]["evidence_path"],
      by_parameter["T2M"]["evidence_path"],
      expr["output_path"],relation["output_path"]
    ]
    if not (
      result.get("returncode")==0
      and result.get("controller_mode")=="MODEL_INDEPENDENT_ACTION_PLAN"
      and result.get("planner_model_last") is None
      and terminal["compiler_clause_coverage_verified"]
      and all((ROOT/p).is_file() for p in required)
    ):
        raise RuntimeError("BRAIN_RETURNED_WITHOUT_REQUIRED_CAUSAL_OUTPUTS")

    evidence={}
    for key,param in [("tmax","T2M_MAX"),("tmin","T2M_MIN"),("tmean","T2M")]:
        rec=json.loads((ROOT/by_parameter[param]["evidence_path"]).read_text(encoding="utf-8"))
        if rec.get("schema")!="PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1":
            raise RuntimeError("SOURCE_EVIDENCE_SCHEMA_INVALID:"+param)
        value=rec.get("value")
        if isinstance(value,bool) or not isinstance(value,(int,float)):
            raise RuntimeError("SOURCE_VALUE_NOT_NUMERIC:"+param)
        evidence[key]=rec

    expr_result=json.loads((ROOT/expr["output_path"]).read_text(encoding="utf-8"))
    relation_result=json.loads((ROOT/relation["output_path"]).read_text(encoding="utf-8"))
    midpoint=float(expr_result["value"])
    delta=float(relation_result["absolute_difference"])
    predicate=relation_result["predicate"]
    if not isinstance(predicate,bool):
        raise RuntimeError("RELATION_PREDICATE_NOT_BOOL")
    if expr_result.get("model_dependency_count")!=0:
        raise RuntimeError("EXPRESSION_MODEL_DEPENDENCY_PRESENT")

    scientific_output={
      "schema":"PROJECT_BRAIN_PARENT_METEOROLOGY_SCIENTIFIC_RESULT_V1",
      "status":"COMPLETED",
      "tmax_c":float(evidence["tmax"]["value"]),
      "tmin_c":float(evidence["tmin"]["value"]),
      "tmean_c":float(evidence["tmean"]["value"]),
      "midpoint_c":midpoint,
      "absolute_midpoint_vs_mean_delta_c":delta,
      "within_3c":predicate,
      "decision":"WITHIN_3C" if predicate else "OUTSIDE_3C",
      "source_urls":[s["url"] for s in task["sources"]],
      "provenance":{
        "tmax":evidence["tmax"],
        "tmin":evidence["tmin"],
        "tmean":evidence["tmean"],
        "expression_artifact":expr["output_path"],
        "relation_artifact":relation["output_path"],
      },
      "model_dependency_count":0,
      "assembly_role":"DETERMINISTIC_BUNDLE_OF_BRAIN_PRODUCED_CAUSAL_ARTIFACTS"
    }
    out=ROOT/task["required_output"]["output_path"]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(scientific_output,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    terminal["scientific_output"]=scientific_output
    terminal["semantic_status"]="PASS"
except Exception as exc:
    terminal["semantic_status"]="FAIL"
    terminal["first_causal_gap"]=type(exc).__name__+":"+str(exc)
    terminal["exception_type"]=type(exc).__name__
    terminal["exception_message"]=str(exc)
    terminal["traceback"]=traceback.format_exc()

(ROOT/"PARENT_METEOROLOGY_TERMINAL.json").write_text(json.dumps(terminal,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("PARENT_METEOROLOGY_SEMANTIC_STATUS="+terminal["semantic_status"])
if terminal.get("first_causal_gap"):
    print("FIRST_CAUSAL_GAP="+terminal["first_causal_gap"])

oracle={
  "schema":"PROJECT_BRAIN_PARENT_METEOROLOGY_INDEPENDENT_ORACLE_V1",
  "source_task_replayed":False,
  "producer_runtime_imported":False,
  "model_dependency_count":0
}
if terminal["semantic_status"]!="PASS":
    oracle["status"]="NOT_RUN_DUE_TO_BRAIN_SEMANTIC_FAILURE"
    oracle["first_causal_gap"]=terminal.get("first_causal_gap")
else:
    def fetch(source):
        req=urllib.request.Request(source["url"],headers={"User-Agent":"ProjectBrain-Independent-Meteorology-Oracle/1"})
        with urllib.request.urlopen(req,timeout=30) as resp:
            raw=resp.read(3000000)
            if resp.status!=200:
                raise RuntimeError("ORACLE_HTTP_STATUS:"+str(resp.status))
        payload=json.loads(raw.decode("utf-8"))
        cur=payload
        for key in source["json_path"]:
            cur=cur[key]
        if isinstance(cur,bool) or not isinstance(cur,(int,float)):
            raise RuntimeError("ORACLE_VALUE_NOT_NUMERIC:"+source["id"])
        return float(cur),hashlib.sha256(raw).hexdigest()
    values={}; hashes={}
    for source in task["sources"]:
        value,sha=fetch(source); values[source["id"]]=value; hashes[source["id"]]=sha
    tmax=values["NASA_POWER_T2M_MAX"]; tmin=values["NASA_POWER_T2M_MIN"]; tmean=values["NASA_POWER_T2M_MEAN"]
    midpoint=(tmax+tmin)/2.0
    delta=abs(midpoint-tmean)
    predicate=delta<=float(task["scientific_contract"]["max_abs_midpoint_vs_mean_delta_c"])
    expected={
      "tmax_c":tmax,"tmin_c":tmin,"tmean_c":tmean,"midpoint_c":midpoint,
      "absolute_midpoint_vs_mean_delta_c":delta,
      "within_3c":predicate,
      "decision":"WITHIN_3C" if predicate else "OUTSIDE_3C",
      "model_dependency_count":0
    }
    observed=terminal["scientific_output"]
    checks={
      "tmax_c":math.isclose(float(observed["tmax_c"]),tmax,rel_tol=0,abs_tol=1e-12),
      "tmin_c":math.isclose(float(observed["tmin_c"]),tmin,rel_tol=0,abs_tol=1e-12),
      "tmean_c":math.isclose(float(observed["tmean_c"]),tmean,rel_tol=0,abs_tol=1e-12),
      "midpoint_c":math.isclose(float(observed["midpoint_c"]),midpoint,rel_tol=0,abs_tol=1e-10),
      "delta":math.isclose(float(observed["absolute_midpoint_vs_mean_delta_c"]),delta,rel_tol=0,abs_tol=1e-10),
      "within_3c":observed["within_3c"] is predicate,
      "decision":observed["decision"]==expected["decision"],
      "model_dependency_count":observed["model_dependency_count"]==0
    }
    oracle.update({
      "status":"PASS" if all(checks.values()) else "FAIL",
      "source_body_sha256":hashes,
      "expected":expected,
      "checks":checks,
      "method":"fresh direct NASA POWER refetch plus independent Python arithmetic; producer modules not imported"
    })
(ROOT/"PARENT_METEOROLOGY_ORACLE.json").write_text(json.dumps(oracle,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("PARENT_METEOROLOGY_ORACLE_STATUS="+oracle["status"])
