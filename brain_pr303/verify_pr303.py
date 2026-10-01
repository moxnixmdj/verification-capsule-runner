#!/usr/bin/env python3
import importlib.util, inspect, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
MAN=json.loads((ROOT/"manifest.json").read_text())

def require(ok,msg):
    if not ok:
        raise SystemExit("VERIFY_FAIL:"+msg)

# Exact-byte closure against private Git blob SHAs.
for rel,meta in MAN["files"].items():
    p=ROOT.parent/rel
    got=subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
    require(got==meta["git_blob_sha"],"BLOB_MISMATCH:"+rel+":"+got+":"+meta["git_blob_sha"])

# Syntax.
for rel in [
    "canonical/runtime/astra_runtime.py",
    "canonical/runtime/enforce_goal_hierarchy.py",
    "canonical/tests/test_runtime_cognition_provenance.py",
]:
    p=ROOT/rel
    subprocess.check_call([sys.executable,"-m","py_compile",str(p)])

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

astra=load_module("brain_pr303_astra",ROOT/"canonical/runtime/astra_runtime.py")
guard=load_module("brain_pr303_guard",ROOT/"canonical/runtime/enforce_goal_hierarchy.py")

# Runtime provenance semantics and the execute_step hook itself.
r=astra._stamp_cognition_provenance({
    "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
    "planner_model_last":None,
    "final_summary":"ok",
})
require(r["model_dependency_count"]==0,"MODEL_INDEPENDENT_COUNT")
require(r["cognition_dependency_class"]=="MODEL_INDEPENDENT","MODEL_INDEPENDENT_CLASS")
require(r["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1","PROVENANCE_AUTHORITY")

r=astra._stamp_cognition_provenance({
    "controller_mode":"OPTIONAL_MODEL_ADVISORY",
    "planner_model_last":"mistral",
})
require(r["model_dependency_count"]>=1,"ADVISORY_NOT_CONTAMINATED")
require(r["cognition_dependency_class"]=="MODEL_ASSISTED","ADVISORY_CLASS")

r=astra._stamp_cognition_provenance({
    "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
    "trace":[{"result":{"model_dependency_count":2}}],
})
require(r["model_dependency_count"]==2,"NESTED_DEPENDENCY_NOT_PROPAGATED")

try:
    astra._stamp_cognition_provenance({"model_dependency_count":-1})
except astra.Blocker:
    pass
else:
    raise SystemExit("VERIFY_FAIL:NEGATIVE_DEPENDENCY_NOT_REJECTED")

orig=astra.run_goal
astra.run_goal=lambda step,mission:{
    "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
    "planner_model_last":None,
    "final_summary":"hook",
}
try:
    hooked=astra.execute_step({"adapter":"goal"},mission={})
finally:
    astra.run_goal=orig
require(hooked["cognition_provenance_authority"]=="ASTRA_RUNTIME_DERIVED_V1","EXECUTE_STEP_NOT_STAMPED")
require(hooked["model_dependency_count"]==0,"EXECUTE_STEP_MODEL_COUNT")

# Canonical frontier mirrors must already agree on exact PR303 bytes.
pointer=json.loads((ROOT/"canonical/CANONICAL_POINTER.json").read_text())
hier=json.loads((ROOT/"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json").read_text())
queue=json.loads((ROOT/"canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json").read_text())
score=json.loads((ROOT/"canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json").read_text())
current=pointer.get("current_frontier") or {}
immediate=queue.get("immediate_frontier") or {}
require(str(current.get("active_capability_target") or "")==str(hier.get("active_capability_target") or ""),"POINTER_HIER_TARGET")
require(str(current.get("critical_blocker") or "")==str(hier.get("current_parent_blocker") or ""),"POINTER_HIER_BLOCKER")
require(str(current.get("next_step") or "")==str(hier.get("next_required_action_class") or ""),"POINTER_HIER_ACTION")
require(str(immediate.get("exact_blocker") or "")==str(hier.get("current_parent_blocker") or ""),"QUEUE_HIER_BLOCKER")
require(str(immediate.get("next_action") or "")==str(hier.get("next_required_action_class") or ""),"QUEUE_HIER_ACTION")
acc=score.get("active_frontier_accounting") or {}
require(str(acc.get("parent_frontier_capability") or "")==str(hier.get("active_capability_target") or ""),"SCORE_HIER_TARGET")
require(str(score.get("next_progress_event_target") or "")==str(hier.get("next_required_action_class") or ""),"SCORE_HIER_ACTION")

# Promotion contract is tightened, not weakened.
front=json.loads((ROOT/"canonical/capabilities/frontier/OPEN_ENDED_AGENTIC_TECHNICAL_RESEARCH_AND_SCIENTIFIC_PROBLEM_SOLVING_V1.json").read_text())
minimum=front.get("minimum_acquisition_evidence") or {}
require(minimum.get("runtime_derived_cognition_provenance_required") is True,"MIN_RUNTIME_PROVENANCE")
require(minimum.get("required_cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1","MIN_PROVENANCE_AUTH")
require(minimum.get("required_producer_model_dependency_count")==0,"MIN_ZERO_MODEL")
require(minimum.get("advisory_model_controller_modes_ineligible") is True,"ADVISORY_INELIGIBLE")
require(minimum.get("nonempty_planner_model_ineligible") is True,"PLANNER_INELIGIBLE")
fw=front.get("promotion_firewall") or {}
require(fw.get("status")=="RUNTIME_PROVENANCE_REQUIRED","FIREWALL_STATUS")
require(fw.get("runtime_authority")=="ASTRA_RUNTIME_DERIVED_V1","FIREWALL_AUTH")
require(fw.get("model_dependency_count_required")==0,"FIREWALL_COUNT")
require(fw.get("canonical_mirror_consistency_required") is True,"FIREWALL_MIRROR")

# Guard helper and exact fail-closed hooks.
vals=guard._collect_key_values(
    {"a":[{"model_dependency_count":0},{"x":{"model_dependency_count":2}}]},
    "model_dependency_count",
)
require(vals==[0,2],"GUARD_RECURSIVE_COLLECT")
src=(ROOT/"canonical/runtime/enforce_goal_hierarchy.py").read_text()
for marker in [
    "COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_COUNT_MISSING",
    "COGNITIVE_PROMOTION_RUNTIME_MODEL_DEPENDENCY_NONZERO",
    "COGNITIVE_PROMOTION_RUNTIME_PROVENANCE_AUTHORITY_MISSING",
    "COGNITIVE_PROMOTION_ADVISORY_MODEL_CONTROLLER_PRESENT",
    "COGNITIVE_PROMOTION_PLANNER_MODEL_PRESENT",
    "POINTER_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
    "POINTER_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
    "POINTER_HIERARCHY_NEXT_ACTION_MISMATCH",
    "QUEUE_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
    "QUEUE_HIERARCHY_NEXT_ACTION_MISMATCH",
    "SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
    "SCOREBOARD_HIERARCHY_NEXT_ACTION_MISMATCH",
]:
    require(marker in src,"MISSING_GUARD_MARKER:"+marker)

print("BRAIN_PR303_GOVERNANCE_VERIFY_PASS")
