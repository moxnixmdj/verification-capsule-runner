#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "verify_pr307_astra_runtime.py":"f11fe4381a66c1d95715dbe8ac2c3a3c5220382a",
 "verify_pr307_enforce_goal_hierarchy.py":"8381f1119d514e8942df534e4e26b5e415205eca",
}
def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for rel,sha in EXPECTED.items():
    got=git_blob_sha(ROOT/rel)
    assert got==sha,(rel,got,sha)

spec=importlib.util.spec_from_file_location("pr307_runtime",ROOT/"verify_pr307_astra_runtime.py")
runtime=importlib.util.module_from_spec(spec); sys.modules[spec.name]=runtime; spec.loader.exec_module(runtime)

r=runtime._stamp_cognition_provenance({
 "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
 "planner_source":None,"planner_transport":None,"planner_model_last":None,
 "final_summary":"ok"})
assert r["model_dependency_count"]==0
assert r["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert r["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1"

r=runtime._stamp_cognition_provenance({
 "controller_mode":"OPTIONAL_MODEL_ADVISORY",
 "planner_source":"planner","planner_transport":"local","planner_model_last":"mistral"})
assert r["model_dependency_count"]>=1 and r["cognition_dependency_class"]=="MODEL_ASSISTED"

for bad in [
 {"final_summary":"ambiguous"},
 {"controller_mode":"UNCLASSIFIED_CONTROLLER","final_summary":"ambiguous"},
]:
    try:
        runtime._stamp_cognition_provenance(bad)
        raise AssertionError(("fail-open provenance",bad))
    except runtime.Blocker:
        pass

r=runtime._stamp_cognition_provenance({
 "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
 "planner_source":"unexpected-planner","planner_transport":None,"planner_model_last":None})
assert r["model_dependency_count"]>=1 and r["cognition_dependency_class"]=="MODEL_ASSISTED"

nested={}; cur=nested
for _ in range(26):
    cur["child"]={}; cur=cur["child"]
try:
    runtime._stamp_cognition_provenance({
      "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","trace":nested})
    raise AssertionError("depth overflow did not fail closed")
except runtime.Blocker:
    pass

gspec=importlib.util.spec_from_file_location("pr307_guard",ROOT/"verify_pr307_enforce_goal_hierarchy.py")
guard=importlib.util.module_from_spec(gspec); sys.modules[gspec.name]=guard; gspec.loader.exec_module(guard)

snap=json.loads((ROOT/"verify_pr307_snapshot.json").read_text())
h=snap["hierarchy"]; t=snap["target"]
hierarchy={"active_capability_target":h["target"],"current_parent_blocker":h["blocker"],"next_required_action_class":h["next"]}
target={"capability_id":t["capability_id"],"residual_gap":t["residual_gap"],"next_action":t["next_action"]}
assert guard.active_target_mirror_errors(hierarchy,target)==[]
guard.FAIL.clear()
guard.enforce_active_target_record_consistency(hierarchy,target)
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

source=(ROOT/"verify_pr307_enforce_goal_hierarchy.py").read_text()
for token in [
 "ACTIVE_FRONTIER_TARGET_RECORD_MISSING",
 "TARGET_RECORD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
 "TARGET_RECORD_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
 "TARGET_RECORD_HIERARCHY_NEXT_ACTION_MISMATCH",
 "CANONICAL_FRONTIER_CROSS_SURFACE_CONSISTENCY_NOT_REQUIRED",
 "RUNTIME_COGNITION_PROVENANCE_NOT_REQUIRED_FOR_COGNITIVE_CREDIT",
]:
    assert token in source,token

report={
 "schema":"PROJECT_BRAIN_PR307_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "brain_pr":307,
 "brain_head":"0cdcaf60f16eaa3ff85dc0c5023abb524bda756c",
 "runtime_blob":"f11fe4381a66c1d95715dbe8ac2c3a3c5220382a",
 "guard_blob":"8381f1119d514e8942df534e4e26b5e415205eca",
 "runtime_fail_closed_cases_verified":5,
 "active_target_mirror_positive_verified":True,
 "active_target_mirror_negative_cases_verified":3,
 "incremental_spend_usd":0
}
(ROOT/"verify-pr307-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
