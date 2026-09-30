#!/usr/bin/env python3
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "execution_guard"))
from actions_admission import problem_sha256

TASK = "canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
MISSION = "canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
RUNTIME = "canonical/runtime/astra_runtime.py"
AUTH = "canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json"
OUT = "guarded_http2_parent_task_a_plan.json"

def sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

task = json.loads((ROOT / TASK).read_text(encoding="utf-8"))
goal = task["goal_text"]

pins = [
    ("execution_guard/github_actions_guarded_run_live.py","30ea2fd2cc548444477c7b234a59129ff8386235"),
    ("execution_guard/actions_admission.py","6c46abef66c036f5382d5792b11a82a289b4dd94"),
    ("execution_guard/github_ref_store_live.py","a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"),
    (AUTH,"0fd94d0b522053161a99da66265d375da5a3aa6c"),
    (TASK,"539cadd30e7e8ac548638157b7f36a1814b97dcd"),
    (MISSION,"fac316bc6d273bf84e06843a6850d358fd3a2e56"),
    ("canonical/capabilities/frontier/OPEN_ENDED_AGENTIC_TECHNICAL_RESEARCH_AND_SCIENTIFIC_PROBLEM_SOLVING_V1.json","a07a230c115e60b2b380fc2ee29e9ae8605a6908"),
    ("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json","55e13c82e17ecbd18063fdbbcfe53ea354905a14"),
    (RUNTIME,"e60345e3814deacc5b79ffd7fcf713febfee0425"),
    ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
    ("canonical/runtime/EPISTEMIC_POLICY_V1.json","baab96f37ba87edc3fdcf6914016cf6593eea102"),
    ("canonical/runtime/PROVIDER_POLICY_V1.json","f74dd63603cb042c107c3743a0af673c272470d8"),
    ("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
    ("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
    ("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
    ("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","da42f0615380027f963044f80e55ddfa1d73ced1"),
    ("canonical/runtime/bound_capabilities/broad_objective_decompose.py","6eb2b20e860da466ad8b793c20060ded1fbf389b"),
    ("canonical/runtime/bound_capabilities/open_research_source_frontend.py","46fe82d74a35d9318a134fb95e1d5cecfc2dd485"),
    ("canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py","816c37742b23739e74a9455a97dd6aea9e767206"),
    ("canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py","1dc26e68d18010b66211d1d83f7b2024c8ad1fcf"),
    ("canonical/runtime/bound_capabilities/objective_relevance_bm25.py","95d2b6bac6f6ffb5db97526407fcd22cbcc6c790"),
    ("canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py","fc45fb583f6aeac91f7c88f918644c38fbc70e34"),
    ("canonical/runtime/bound_capabilities/source_authority_binding_ror.py","9396ff7169b274af9bbfbe736e004587631e3b05"),
    ("canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","48fd058430d8d361fc75beced567c7b6d1166531"),
    ("canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py","d66a7eb30774f66160b698d8082947776888293d"),
    ("canonical/runtime/bound_capabilities/grounded_executable_composition.py","8328e12804f64cab1c0d9509966cb1d2d8fb1f82"),
    ("canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py","ab9f6fc19937d23edb24dc26a2affed96cea0a9a"),
]

plan = {
    "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
    "goal_text":goal,
    "frozen":{
        "gate_id":"BRAIN-HTTP2-PARENT-TASK-A-GUARDED-EXECUTION-20260930-V1",
        "problem_sha256":problem_sha256(goal),
        "task_sha256":sha256(TASK),
        "runtime_sha256":sha256(RUNTIME),
        "canonical_base":"f0f87c981d77b552caa21844e6bcc7b83116f339",
        "authorization_sha256":sha256(AUTH),
    },
    "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in pins],
    "command":["python",RUNTIME,MISSION],
    "authority":{
        "brain_task_freeze_pr":455,
        "brain_guarded_execution_authorization_pr":458,
        "brain_authorization_commit":"f0f87c981d77b552caa21844e6bcc7b83116f339",
        "guarded_claim_spec_requalification_run":36686583882,
        "prior_rejected_carrier_pr":456,
        "prior_rejected_carrier_execution_count":0,
        "parent_task_replay":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0
    }
}
(ROOT / OUT).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"plan":OUT,"problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"],"authorization_sha256":plan["frozen"]["authorization_sha256"]},sort_keys=True))
