#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "canonical"
RUNTIME = CANON / "runtime"
GOV = CANON / "governance"
VER = CANON / "verification"

EXPECTED = {
    "canonical/runtime/r2_direct_route_dynamic_admission_v1.py": "65fc5bdb5283944d058c6c6a2ff1fe360aa17489",
    "canonical/runtime/promote_r2_direct_route_v1.py": "85be8711c55243a8355094d766ced625a30062c7",
    "canonical/runtime/r2_direct_live_admission_v1.py": "c995e4cad77e68268e18b059c97f00936283e6b6",
    "canonical/runtime/unified_cognitive_fabric_v1.py": "5eaea605c4e441ef33180bd76a951a9f973dc40f",
}

def blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def blob(path: Path) -> str:
    return blob_bytes(path.read_bytes())

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def write_json(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def eq(a, b, label):
    if a != b:
        raise AssertionError(f"{label}: {a!r} != {b!r}")

def ok(v, label):
    if not v:
        raise AssertionError(label)

for rel, expected in EXPECTED.items():
    eq(blob(ROOT / rel), expected, "exact source blob " + rel)

write(CANON / "__init__.py", "")
write(RUNTIME / "__init__.py", "")
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Part A: exact route-admission + promotion source over a synthetic V20 carrier.
# ---------------------------------------------------------------------------
legacy = types.ModuleType("canonical.runtime.r2_direct_end_to_end_adequacy_v20")
legacy.ROUTES = {"LEGACY": {"capability_id": "legacy"}}
legacy_state = {"preflight": {"matched": False, "status": "NO"}, "runs": 0}
def legacy_preflight(request, repo_root=None):
    return dict(legacy_state["preflight"])
def legacy_run(request, repo_root=None):
    legacy_state["runs"] += 1
    return {"pass": True, "route_id": "LEGACY", "status": "PASS_LEGACY"}
legacy.preflight = legacy_preflight
legacy.run = legacy_run
sys.modules[legacy.__name__] = legacy

admission = importlib.import_module("canonical.runtime.r2_direct_route_dynamic_admission_v1")
promoter = importlib.import_module("canonical.runtime.promote_r2_direct_route_v1")
wrapper = importlib.import_module("canonical.runtime.r2_direct_live_admission_v1")

write(RUNTIME / "dynamic_c.py", """def preflight(request, repo_root=None):
    g=str(request.get('goal') or '')
    if g == 'dyn-open':
        return {'matched': False, 'direct_route_semantic_open': True, 'route_id': 'DYNAMIC_C'}
    return {'matched': g in {'c','overlap'}, 'route_id': 'DYNAMIC_C'}
def run(request, repo_root=None):
    return {'pass': True, 'route_id': 'DYNAMIC_C', 'status': 'PASS_DYNAMIC'}
""")
write_json(VER / "dynamic_c_verify.json", {"status": "PASS"})

empty_manifest = {
    "schema": admission.MANIFEST_SCHEMA,
    "status": "ACTIVE_DYNAMIC_ADMISSIONS__EMPTY",
    "selection_class": admission.SELECTION_CLASS,
    "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
    "admission_count": 0,
    "admissions": [],
}
empty_path = GOV / "R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_EMPTY.json"
write_json(empty_path, empty_manifest)
write_json(GOV / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json", {
    "schema": admission.POINTER_SCHEMA,
    "date": "2026-10-09",
    "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
    "binding_semantics": "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
    "target": {
        "path": "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_EMPTY.json",
        "git_blob_sha": blob(empty_path),
        "schema": admission.MANIFEST_SCHEMA,
    },
    "incremental_spend_usd": 0,
    "terminal_authority": False,
    "terminal_credit_delta": 0,
})

# Empty dynamic state must be exact legacy delegation.
legacy_state["preflight"] = {"matched": True, "route_id": "LEGACY", "status": "LEGACY_MATCH"}
eq(wrapper.preflight({"task_id":"t","goal":"x"}, repo_root=ROOT), legacy_state["preflight"], "empty admission exact preflight delegation")
legacy_state["runs"] = 0
out = wrapper.run({"task_id":"t","goal":"x"}, repo_root=ROOT)
ok(out["pass"], "empty admission legacy run")
eq(legacy_state["runs"], 1, "legacy run called once")

candidate = {
    "schema": admission.CANDIDATE_SCHEMA,
    "route_id": "DYNAMIC_C",
    "capability_id": "capsule.dynamic.c",
    "runtime_path": "canonical/runtime/dynamic_c.py",
    "runtime_git_blob_sha": blob(RUNTIME / "dynamic_c.py"),
    "preflight_callable": "preflight",
    "run_callable": "run",
    "route_verification_path": "canonical/verification/dynamic_c_verify.json",
    "route_verification_git_blob_sha": blob(VER / "dynamic_c_verify.json"),
    "scope": "capsule://dynamic-c",
    "selection_class": admission.SELECTION_CLASS,
    "deployment_requested": True,
    "incremental_spend_usd": 0,
    "terminal_authority": False,
}
cand_path = GOV / "DYNAMIC_C_CANDIDATE.json"
write_json(cand_path, candidate)
receipt = {
    "schema": admission.RECEIPT_SCHEMA,
    "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
    "candidate_path": "canonical/governance/DYNAMIC_C_CANDIDATE.json",
    "candidate_git_blob_sha": blob(cand_path),
    "route_id": "DYNAMIC_C",
    "runtime_path": candidate["runtime_path"],
    "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
    "route_verification_path": candidate["route_verification_path"],
    "route_verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
    "selection_class": admission.SELECTION_CLASS,
    "independent_verified": True,
    "preflight_pure_no_effect": True,
    "matched_route_failure_no_fallthrough": True,
    "producer_independent_acceptance": True,
    "exact_raw_obligation_acceptance": True,
    "deployment_eligible": True,
    "verification_authority_mutated": False,
    "promotion_authority": False,
    "terminal_authority": False,
    "incremental_spend_usd": 0,
}
receipt_path = VER / "DYNAMIC_C_RECEIPT.json"
write_json(receipt_path, receipt)
promotion = promoter.promote(
    candidate_path="canonical/governance/DYNAMIC_C_CANDIDATE.json",
    receipt_path="canonical/verification/DYNAMIC_C_RECEIPT.json",
    repo_root=ROOT,
)
ok(promotion["pass"], "promotion pass")
ok(promotion["frontier_changed"], "promotion changed frontier")
eq(promotion["status"], "PASS__R2_DIRECT_ROUTE_PROMOTED_AND_CURRENT_POINTER_REPLAYED", "promotion status")

legacy_state["preflight"] = {"matched": False, "status": "NO"}
pf = wrapper.preflight({"task_id":"t","goal":"c"}, repo_root=ROOT)
eq(pf["route_id"], "DYNAMIC_C", "unique dynamic selected")
out = wrapper.run({"task_id":"t","goal":"c"}, repo_root=ROOT)
ok(out["pass"], "dynamic run pass")
eq(out["status"], "PASS_DYNAMIC", "dynamic run status")

legacy_state["preflight"] = {"matched": True, "route_id": "LEGACY", "status": "LEGACY_MATCH"}
collision = wrapper.preflight({"task_id":"t","goal":"overlap"}, repo_root=ROOT)
eq(collision["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION", "dynamic legacy overlap closed")
eq(collision["reason"], "DYNAMIC_ROUTE_OVERLAPS_LEGACY_V20", "overlap reason")

legacy_state["preflight"] = {"matched": False, "direct_route_semantic_open": True, "route_id":"LEGACY_OPEN"}
collision2 = wrapper.preflight({"task_id":"t","goal":"overlap"}, repo_root=ROOT)
eq(collision2["status"], "FAIL_CLOSED__DIRECT_ROUTE_COLLISION", "dynamic legacy open overlap closed")

legacy_state["preflight"] = {"matched": False, "status": "NO"}
dyn_open = wrapper.preflight({"task_id":"t","goal":"dyn-open"}, repo_root=ROOT)
eq(dyn_open["status"], "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY", "dynamic semantic open closed")

again = promoter.promote(
    candidate_path="canonical/governance/DYNAMIC_C_CANDIDATE.json",
    receipt_path="canonical/verification/DYNAMIC_C_RECEIPT.json",
    repo_root=ROOT,
)
ok(again["pass"], "idempotent promotion pass")
ok(again["frontier_changed"] is False, "idempotent promotion no mutation")

# ---------------------------------------------------------------------------
# Part B: import exact Unified Cognitive Fabric with unrelated dependencies stubbed.
# ---------------------------------------------------------------------------

def module(name, **attrs):
    m=types.ModuleType(name)
    for k,v in attrs.items():
        setattr(m,k,v)
    sys.modules[name]=m
    return m

decision_results = []
closure_result = {}
decision_calls = []

def live_run(request, **kwargs):
    if request.get("mode") == "decision":
        decision_calls.append(json.loads(json.dumps(request)))
        if not decision_results:
            raise AssertionError("unexpected decision replay")
        inner = decision_results.pop(0)
        return {
            "pass": inner.get("pass") is True,
            "status": "UNIFIED_DECISION_EXECUTION_COMPLETE",
            "decision_output": inner,
            "learning": None,
            "reuse_first": False,
            "reused_skill_id": None,
            "terminal_authority": False,
        }
    raise AssertionError("unexpected live_runtime mode " + str(request.get("mode")))

live_runtime = module(
    "canonical.runtime.live_brain_runtime_v1",
    run=live_run,
    SURFACES={},
    observe_runtime_outcome=lambda *a,**k: None,
    execute_failure_repair_cycle=lambda *a,**k: {"pass":False},
    synthesize_failure_repair=lambda *a,**k: {"pass":False},
)

module("canonical.runtime.live_integrated_brain_v1", load_verified_registry=lambda: {})
module("canonical.runtime.p3_real_context_v3_admission_v12", evaluate=lambda *a,**k: {"pass":False})
module(
    "canonical.runtime.autonomous_verified_self_improvement_v1",
    DEFAULT_STATE_PATH=ROOT/"state.json",
    load_state=lambda *a,**k: {"stats":{}},
    run_learning_episode=lambda *a,**k: {"pass":False},
)
module(
    "canonical.runtime.r3_improvement_queue_driver_v1",
    drain=lambda *a,**k: {"pass":True,"status":"NOOP","terminal_authority":False},
)
module("canonical.runtime.h100_verified_capability_registry_v8", registry_snapshot=lambda: {"entry_count":0})
module("canonical.runtime.exact_linear_parameter_polytope_v1", solve=lambda x: {"pass":False})
module("canonical.runtime.interval_information_frontier_v1", solve=lambda x: {"pass":False})
module("canonical.runtime.capability_first_scheduler_v1", rank_work=lambda x: {"ranked":[]})
module("canonical.runtime.brain_owned_python_closure_census_v1", census=lambda *a,**k: {"brain_owned_file_count":1,"brain_owned_transitive_source_bytes":1,"brain_owned_transitive_files":[]})
module("canonical.runtime.current_authority_runtime_census_v1", run=lambda *a,**k: {"pass":True,"authority_pointer_reference_missing_count":0,"authority_pointer_reference_missing_paths":[],"authority_pointer_runtime_reference_count":1})
module("canonical.runtime.live_capability_ownership_v1", evaluate=lambda *a,**k: {"r1_structural_closure":True,"provider_coverage_complete":True,"live_owned_capability_ids":[],"live_owned_capability_count":0,"live_owned_equals_fabric_reachable":True})
module("canonical.runtime.live_capability_invoker_v1", coverage=lambda *a,**k: {"pass":True}, invoke=lambda *a,**k: {"pass":False})
module("canonical.runtime.live_capability_composition_v1", execute=lambda *a,**k: {"pass":False})
module("canonical.runtime.r1_live_architecture_closure_gate_v1", evaluate=lambda *a,**k: {"pass":True,"errors":[]})
module("canonical.runtime.universal_escape_resolver_v1", resolve=lambda **k: {"pass":False})
module("canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2", preflight=lambda: {}, dispatch=lambda *a,**k: {})
module("canonical.runtime.terminal_autopilot_v1", build_manifest_from_repo=lambda *a,**k: {}, plan=lambda *a,**k: {})
module("canonical.runtime.terminal_root_decision_gate_v1", evaluate=lambda *a,**k: {"pass":False})
module("canonical.runtime.terminal_closure_reducer", evaluate_manifest=lambda *a,**k: {"achieved":False})
module("canonical.runtime.verified_bound_capability_execution_adapter_v1", execute=lambda *a,**k: {"pass":False})
module("canonical.runtime.semantic_ambiguity_control_v1", decide=lambda *a,**k: {"pass":False})
module("canonical.runtime.semantic_relation_control_v1", resolve=lambda *a,**k: {"pass":False})
module("canonical.runtime.oewn_decision_sense_control_v1", resolve=lambda *a,**k: {"pass":False})
module("canonical.runtime.finance_bounded_concept_registry_verify_v1", CLAIM_SCHEMA="CLAIM", verify_claim=lambda *a,**k: None)

def one_shot_run(**kwargs):
    return json.loads(json.dumps(closure_result))
module("canonical.runtime.one_shot_reality_closure_v2", run=one_shot_run)

# Force exact fabric module import after all stubs are installed.
sys.modules.pop("canonical.runtime.unified_cognitive_fabric_v1", None)
fabric = importlib.import_module("canonical.runtime.unified_cognitive_fabric_v1")

payload={"task_id":"auto","goal":"unresolved"}
unresolved={
    "pass":False,
    "status":"OPEN__DECISION_CONTEXT_REQUIRED",
    "r2_fixed_point_status":"OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
    "terminal_authority":False,
}
solved={
    "pass":True,
    "status":"PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
    "semantic_acceptance_complete":True,
    "actual_goal_satisfaction_verified":True,
    "terminal_authority":False,
}

# Fixed-point closure must replay the exact same decision request and may turn green only on replay pass.
decision_calls.clear(); decision_results[:] = [dict(unresolved), dict(solved)]
closure_result.clear(); closure_result.update({
    "pass":True,
    "status":"PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
    "fixed_point":True,
    "terminal_authority":False,
})
out=fabric.run({"payload":payload,"options":{"learn":False}})
ok(out["inner_pass"], "AUTO fixed point replay passes")
eq(len(decision_calls),2,"decision called exactly twice")
eq(decision_calls[0],decision_calls[1],"exact decision replay")
ok(out["auto_one_shot_closure"]["replay_attempted"],"replay attempted")
ok(out["auto_one_shot_closure"]["replay_pass"],"replay pass")

# Externality proof must not turn the original task green and must not replay.
decision_calls.clear(); decision_results[:] = [dict(unresolved)]
closure_result.clear(); closure_result.update({
    "pass":True,
    "status":"PASS__PROVEN_INFORMATION_THEORETICALLY_EXTERNAL",
    "fixed_point":True,
    "gap_contract":{"gap_class":"PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"},
    "terminal_authority":False,
})
out=fabric.run({"payload":payload,"options":{"learn":False}})
ok(not out["inner_pass"],"externality does not turn task green")
eq(len(decision_calls),1,"externality does not replay")
ok(out["auto_one_shot_closure"]["proven_external"],"externality marked")

# Explicit ADEQUATE_DECISION must never auto invoke one-shot. Use an impossible closure sentinel.
decision_calls.clear(); decision_results[:] = [dict(unresolved)]
closure_result.clear(); closure_result.update({"SHOULD_NOT_BE_USED":True})
out=fabric.run({"mode":"ADEQUATE_DECISION","payload":payload,"options":{"learn":False}})
ok(not out["auto_routed"],"explicit mode not auto")
eq(len(decision_calls),1,"explicit mode single decision call")
eq(out["auto_one_shot_closure"],None,"explicit mode no auto closure")

# User clarification must skip closure.
decision_calls.clear(); decision_results[:] = [{**unresolved,"ask_user_required":True,"action":"ASK_USER_MINIMUM_CLARIFICATION"}]
out=fabric.run({"payload":payload,"options":{"learn":False}})
eq(len(decision_calls),1,"user clarification no replay")
eq(out["auto_one_shot_closure"],None,"user clarification no one shot")

print(json.dumps({
    "status":"PASS__PR3755_EXACT_CONTROL_LOGIC_ISOLATED_EXECUTION",
    "source_blobs":EXPECTED,
    "route_v20_exact_delegation_verified":True,
    "dynamic_promotion_and_pointer_replay_verified":True,
    "dynamic_unique_execution_verified":True,
    "dynamic_legacy_collision_fail_closed_verified":True,
    "dynamic_semantic_open_fail_closed_verified":True,
    "idempotent_promotion_verified":True,
    "auto_one_shot_fixed_point_exact_replay_verified":True,
    "externality_does_not_turn_task_green_verified":True,
    "explicit_mode_skips_auto_one_shot_verified":True,
    "user_clarification_skips_auto_one_shot_verified":True,
    "full_private_repository_regression_suite_verified":False,
    "terminal_authority":False,
},indent=2,sort_keys=True))
