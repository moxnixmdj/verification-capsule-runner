#!/usr/bin/env python3
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
MISSION="canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
RUNTIME="canonical/runtime/astra_runtime.py"
AUTH="canonical/action_intents/2026-09-30_FREEZE_FRESH_GENOMICS_REFERENCE_LENGTH_OPENENDED_PARENT_TASK_A_V1.json"
PLAN_OUT="guarded_http2_parent_task_a_plan.json"
TERMINAL_OUT="http2-parent-task-terminal.json"

PINNED=[
    TASK,
    MISSION,
    RUNTIME,
    AUTH,
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
    "canonical/runtime/goal_compiler.py",
    "canonical/runtime/capability_proposal_generators.py",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
    "canonical/runtime/bound_capabilities/broad_objective_decompose.py",
    "canonical/runtime/bound_capabilities/open_research_source_frontend.py",
    "canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py",
    "canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py",
    "canonical/runtime/bound_capabilities/objective_relevance_bm25.py",
    "canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py",
    "canonical/runtime/bound_capabilities/objective_claim_operand_binding.py",
    "canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py",
    "canonical/runtime/bound_capabilities/source_authority_binding_ror.py",
    "canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py",
    "canonical/runtime/bound_capabilities/evidence_decision_synthesis.py",
    "canonical/runtime/bound_capabilities/evidence_decision_verify.py",
    "canonical/runtime/bound_capabilities/grounded_executable_composition.py",
    "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py",
    "execution_guard/github_actions_guarded_run_live.py",
    "execution_guard/actions_admission.py",
    "execution_guard/github_ref_store_live.py",
]

def data(rel):
    return (ROOT/rel).read_bytes()

def sha256_file(rel):
    return hashlib.sha256(data(rel)).hexdigest()

def git_blob_sha1(rel):
    raw=data(rel)
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())

plan={
    "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
    "goal_text":goal,
    "frozen":{
        "gate_id":"BRAIN-PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-TASK-B-20260930-005-V1",
        "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest(),
        "task_sha256":sha256_file(TASK),
        "runtime_sha256":sha256_file(RUNTIME),
        "canonical_base":"3866a84b87248fe2b80b54301370b75c00245869",
        "authorization_sha256":sha256_file(AUTH),
    },
    "pinned_files":[{"path":p,"git_blob_sha1":git_blob_sha1(p)} for p in PINNED],
    "command":[
        "bash","-lc",
        "set -o pipefail; ASTRA_DISABLE_MODEL_PLANNER=1 python "
        "canonical/runtime/astra_runtime.py "
        "canonical/astra_runtime/missions/"
        "PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json "
        "2>&1 | tee "+TERMINAL_OUT,
    ],
    "authority":{
        "kind":"FRESH_PARENT_TASK_B_SINGLE_PHYSICAL_EXECUTION",
        "brain_pr_freeze":478,
        "brain_canonical_main":"3866a84b87248fe2b80b54301370b75c00245869",
        "broad_routing_repair_pr":474,
        "broad_routing_guarded_qualification_run":36689721937,
        "prior_http2_parent_run":36688193204,
        "prior_http2_task_replay_allowed":False,
        "parent_task_execution":True,
        "parent_task_replay":False,
        "no_same_task_replay":True,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    },
}
(ROOT/PLAN_OUT).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({
    "status":"GENOMICS_PLAN_GENERATED",
    "problem_sha256":plan["frozen"]["problem_sha256"],
    "task_sha256":plan["frozen"]["task_sha256"],
    "runtime_sha256":plan["frozen"]["runtime_sha256"],
    "pin_count":len(plan["pinned_files"]),
},sort_keys=True))
