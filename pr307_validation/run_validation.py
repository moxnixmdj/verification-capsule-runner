#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys, traceback

ROOT=pathlib.Path(__file__).resolve().parent
REPORT=ROOT/"pr307-validation-report.json"
EXPECTED={
  "brain_head":"785e93aa017ddfe99b116194eefedc19cf03b09f",
  "astra_runtime_blob":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "enforce_goal_hierarchy_blob":"8381f1119d514e8942df534e4e26b5e415205eca",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

checks={}
try:
    checks["runtime_blob_exact"]=git_blob_sha(ROOT/"astra_runtime.py")==EXPECTED["astra_runtime_blob"]
    checks["guard_blob_exact"]=git_blob_sha(ROOT/"enforce_goal_hierarchy.py")==EXPECTED["enforce_goal_hierarchy_blob"]
    assert all(checks.values()), checks

    runtime=load("pr307_astra_runtime",ROOT/"astra_runtime.py")
    guard=load("pr307_enforce_goal_hierarchy",ROOT/"enforce_goal_hierarchy.py")

    independent={
      "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
      "planner_source":None,
      "planner_transport":None,
      "planner_model_last":None,
      "final_summary":"ok",
    }
    stamped=runtime._stamp_cognition_provenance(independent)
    checks["model_independent_zero"]=(
      stamped.get("model_dependency_count")==0
      and stamped.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
      and stamped.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
    )

    for label,payload,needle in [
      ("missing_mode_fails",{"final_summary":"x"},"COGNITION_PROVENANCE_CONTROLLER_MODE_MISSING"),
      ("unknown_mode_fails",{"controller_mode":"UNKNOWN","final_summary":"x"},"COGNITION_PROVENANCE_CONTROLLER_MODE_UNKNOWN"),
      ("negative_count_fails",{"controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","model_dependency_count":-1},"MODEL_DEPENDENCY_COUNT_INVALID"),
    ]:
      try:
        runtime._stamp_cognition_provenance(payload)
      except runtime.Blocker as exc:
        checks[label]=needle in str(exc)
      else:
        checks[label]=False

    contaminated=runtime._stamp_cognition_provenance({
      "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
      "planner_source":"unexpected",
      "planner_transport":None,
      "planner_model_last":None,
    })
    checks["planner_marker_contaminates"]=(
      int(contaminated.get("model_dependency_count",-1))>=1
      and contaminated.get("cognition_dependency_class")=="MODEL_ASSISTED"
    )

    original=runtime._run_goal_unstamped
    try:
      runtime._run_goal_unstamped=lambda step,mission: dict(independent)
      direct=runtime.run_goal({}, {})
    finally:
      runtime._run_goal_unstamped=original
    checks["direct_run_goal_stamped"]=(
      direct.get("model_dependency_count")==0
      and direct.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
    )

    original=runtime._run_goal_unstamped
    try:
      runtime._run_goal_unstamped=lambda step,mission: {
        "controller_mode":"OPTIONAL_MODEL_ADVISORY",
        "planner_source":"x","planner_transport":"x","planner_model_last":"x",
        "final_summary":"x",
      }
      direct_model=runtime.run_goal({}, {})
    finally:
      runtime._run_goal_unstamped=original
    checks["direct_model_path_not_zero"]=(
      int(direct_model.get("model_dependency_count",0))>=1
      and direct_model.get("cognition_dependency_class")=="MODEL_ASSISTED"
    )

    h={"active_capability_target":"CAP_A","current_parent_blocker":"BLOCK_A","next_required_action_class":"ACT_A"}
    t={"capability_id":"CAP_A","residual_gap":"BLOCK_A","next_action":"ACT_A"}
    checks["target_mirror_exact_pass"]=guard.active_target_mirror_errors(h,t)==[]
    for field,bad,expected in [
      ("capability_id","CAP_B","FRONTIER_TARGET_CAPABILITY_ID_MISMATCH"),
      ("residual_gap","BLOCK_B","FRONTIER_TARGET_RESIDUAL_GAP_MISMATCH"),
      ("next_action","ACT_B","FRONTIER_TARGET_NEXT_ACTION_MISMATCH"),
    ]:
      x=dict(t); x[field]=bad
      checks["target_"+field+"_drift_fails"]=expected in guard.active_target_mirror_errors(h,x)

    status="PASS" if all(checks.values()) else "FAIL"
    report={"schema":"BRAIN_PR307_EXACT_VALIDATION_V1","status":status,"expected":EXPECTED,"checks":checks}
except Exception as exc:
    report={"schema":"BRAIN_PR307_EXACT_VALIDATION_V1","status":"ERROR","expected":EXPECTED,"checks":checks,
            "error":type(exc).__name__+":"+str(exc),"traceback":traceback.format_exc().splitlines()[-30:]}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["status"]=="PASS" else 1)
