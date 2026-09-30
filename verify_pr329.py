#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, py_compile, sys
ROOT=pathlib.Path(__file__).resolve().parent
BRAIN_HEAD="1f0f752b91aa0cd69770ed7b26718a71fd83d00b"
EXPECTED={
 "verify_pr329_astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
 "verify_pr329_enforce_goal_hierarchy.py":"8381f1119d514e8942df534e4e26b5e415205eca",
}
def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for rel,sha in EXPECTED.items():
    got=git_blob_sha(ROOT/rel)
    assert got==sha,(rel,got,sha)
    py_compile.compile(str(ROOT/rel),doraise=True)

spec=importlib.util.spec_from_file_location("pr329_runtime",ROOT/"verify_pr329_astra_runtime.py")
runtime=importlib.util.module_from_spec(spec); sys.modules[spec.name]=runtime; spec.loader.exec_module(runtime)

base={"controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","planner_source":None,"planner_transport":None,"planner_model_last":None,"final_summary":"ok"}
r=runtime._stamp_cognition_provenance(base)
assert r["model_dependency_count"]==0
assert r["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert r["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1"

for bad in [
 {"final_summary":"ambiguous"},
 {"controller_mode":"","final_summary":"ambiguous"},
 {"controller_mode":"UNCLASSIFIED_CONTROLLER","final_summary":"ambiguous"},
]:
    try:
        runtime._stamp_cognition_provenance(bad)
        raise AssertionError(("fail-open provenance",bad))
    except runtime.Blocker:
        pass

for key in ("planner_source","planner_transport","planner_model_last"):
    case=dict(base); case[key]="nonempty"
    r=runtime._stamp_cognition_provenance(case)
    assert r["model_dependency_count"]>=1 and r["cognition_dependency_class"]=="MODEL_ASSISTED",(key,r)

nested={}; cur=nested
for _ in range(26):
    cur["child"]={}; cur=cur["child"]
try:
    runtime._stamp_cognition_provenance({"controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","trace":nested})
    raise AssertionError("depth overflow did not fail closed")
except runtime.Blocker:
    pass

orig=runtime._run_goal_unstamped
try:
    runtime._run_goal_unstamped=lambda step,mission: dict(base)
    direct=runtime.run_goal({}, {})
finally:
    runtime._run_goal_unstamped=orig
assert direct["model_dependency_count"]==0
assert direct["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1"

orig=runtime._run_goal_unstamped
try:
    runtime._run_goal_unstamped=lambda step,mission: {
      "controller_mode":"OPTIONAL_MODEL_ADVISORY",
      "planner_source":"model","planner_transport":"test","planner_model_last":"model-x"
    }
    direct=runtime.run_goal({}, {})
finally:
    runtime._run_goal_unstamped=orig
assert direct["model_dependency_count"]>=1 and direct["cognition_dependency_class"]=="MODEL_ASSISTED"

runtime_src=(ROOT/"verify_pr329_astra_runtime.py").read_text()
assert "def _run_goal_unstamped(" in runtime_src
assert "def run_goal(step, mission):" in runtime_src
assert "return _stamp_cognition_provenance(_run_goal_unstamped(step, mission))" in runtime_src
assert 'if adapter=="goal":\n        return run_goal(step, mission or {})' in runtime_src

gspec=importlib.util.spec_from_file_location("pr329_guard",ROOT/"verify_pr329_enforce_goal_hierarchy.py")
guard=importlib.util.module_from_spec(gspec); sys.modules[gspec.name]=guard; gspec.loader.exec_module(guard)
snap=json.loads((ROOT/"verify_pr329_snapshot.json").read_text())
h=snap["hierarchy"]; t=snap["target"]
hierarchy={"active_capability_target":h["target"],"current_parent_blocker":h["blocker"],"next_required_action_class":h["next"]}
target=dict(t)
guard.FAIL.clear(); guard.enforce_active_target_record_consistency(hierarchy,target)
assert guard.FAIL==[],guard.FAIL
for field,bad_value,expected in [
 ("capability_id","STALE","TARGET_RECORD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH"),
 ("residual_gap","STALE","TARGET_RECORD_HIERARCHY_CRITICAL_BLOCKER_MISMATCH"),
 ("next_action","STALE","TARGET_RECORD_HIERARCHY_NEXT_ACTION_MISMATCH"),
]:
    bad=dict(target); bad[field]=bad_value
    guard.FAIL.clear(); guard.enforce_active_target_record_consistency(hierarchy,bad)
    assert expected in guard.FAIL,(field,guard.FAIL)
assert h["next_progress_event_target"]==h["next"]

guard_src=(ROOT/"verify_pr329_enforce_goal_hierarchy.py").read_text()
for token in [
 "ACTIVE_FRONTIER_TARGET_RECORD_MISSING",
 "TARGET_RECORD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
 "TARGET_RECORD_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
 "TARGET_RECORD_HIERARCHY_NEXT_ACTION_MISMATCH",
 "CANONICAL_FRONTIER_CROSS_SURFACE_CONSISTENCY_NOT_REQUIRED",
 "RUNTIME_COGNITION_PROVENANCE_NOT_REQUIRED_FOR_COGNITIVE_CREDIT",
]:
    assert token in guard_src,token

report={
 "schema":"PROJECT_BRAIN_PR329_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "brain_pr":329,
 "brain_head":BRAIN_HEAD,
 "runtime_blob":EXPECTED["verify_pr329_astra_runtime.py"],
 "guard_blob":EXPECTED["verify_pr329_enforce_goal_hierarchy.py"],
 "runtime_fail_closed_cases_verified":7,
 "direct_run_goal_provenance_boundary_verified":True,
 "active_target_mirror_positive_verified":True,
 "active_target_mirror_negative_cases_verified":3,
 "incremental_spend_usd":0
}
(ROOT/"verify-pr329-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
