#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "verify_pr303_astra_runtime.py":"06777da3a97a91290ad01d6a313b970b4334bab2",
 "verify_pr303_enforce_goal_hierarchy.py":"64e9ce4a89966e70ac123210322470099abb574f",
}
def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for rel,sha in EXPECTED.items():
    got=git_blob_sha(ROOT/rel)
    assert got==sha,(rel,got,sha)

spec=importlib.util.spec_from_file_location("pr303_runtime",ROOT/"verify_pr303_astra_runtime.py")
runtime=importlib.util.module_from_spec(spec); sys.modules[spec.name]=runtime; spec.loader.exec_module(runtime)

r=runtime._stamp_cognition_provenance({
 "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","planner_model_last":None,"final_summary":"ok"})
assert r["model_dependency_count"]==0
assert r["cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert r["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1"

r=runtime._stamp_cognition_provenance({
 "controller_mode":"OPTIONAL_MODEL_ADVISORY","planner_model_last":"mistral","final_summary":"ok"})
assert r["model_dependency_count"]>=1 and r["cognition_dependency_class"]=="MODEL_ASSISTED"

r=runtime._stamp_cognition_provenance({
 "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN","trace":[{"result":{"model_dependency_count":2}}]})
assert r["model_dependency_count"]==2 and r["cognition_dependency_class"]=="MODEL_ASSISTED"

try:
    runtime._stamp_cognition_provenance({"model_dependency_count":-1})
    raise AssertionError("negative dependency count did not fail")
except runtime.Blocker:
    pass

guard=(ROOT/"verify_pr303_enforce_goal_hierarchy.py").read_text(encoding="utf-8")
required_tokens=[
 "POINTER_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
 "POINTER_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
 "POINTER_HIERARCHY_NEXT_ACTION_MISMATCH",
 "QUEUE_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
 "QUEUE_HIERARCHY_NEXT_ACTION_MISMATCH",
 "SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
 "SCOREBOARD_HIERARCHY_NEXT_ACTION_MISMATCH",
 "COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_COUNT_MISSING",
 "COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_NONZERO",
 "COGNITIVE_PROMOTION_RUNTIME_PROVENANCE_AUTHORITY_MISSING",
 "COGNITIVE_PROMOTION_ADVISORY_MODEL_CONTROLLER_PRESENT",
 "COGNITIVE_PROMOTION_PLANNER_MODEL_PRESENT",
]
missing=[x for x in required_tokens if x not in guard]
assert not missing,missing

snap=json.loads((ROOT/"verify_pr303_frontier_snapshot.json").read_text(encoding="utf-8"))
p,h,q,s=snap["pointer"],snap["hierarchy"],snap["queue"],snap["scoreboard"]
assert p["target"]==h["target"]==q["target"]==s["target"]
assert p["blocker"]==h["blocker"]==q["blocker"]
assert p["next"]==h["next"]==q["next"]==s["next"]
contract=snap["acquisition_contract"]
assert contract["runtime_derived_cognition_provenance_required"] is True
assert contract["required_cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1"
assert contract["required_producer_model_dependency_count"]==0
assert contract["advisory_model_controller_modes_ineligible"] is True
assert contract["nonempty_planner_model_ineligible"] is True

report={
 "schema":"PROJECT_BRAIN_PR303_TARGETED_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "runtime_provenance_tests":4,
 "validator_guard_tokens_verified":len(required_tokens),
 "frontier_surfaces_consistent":True,
 "cognitive_promotion_contract_hardened":True,
 "incremental_spend_usd":0,
}
(ROOT/"verify-pr303-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
