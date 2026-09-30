#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
MISSION="canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json"
RUNTIME="canonical/runtime/astra_runtime.py"
AUTH="canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-20260930-003-V1",
    "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest(),
    "task_sha256":sha256_file(TASK),
    "runtime_sha256":sha256_file(RUNTIME),
    "canonical_base":"f0f87c981d77b552caa21844e6bcc7b83116f339",
    "authorization_sha256":sha256_file(AUTH)
  },
  "pinned_files":[
  {
    "path": "canonical/tasks/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
    "git_blob_sha1": "539cadd30e7e8ac548638157b7f36a1814b97dcd"
  },
  {
    "path": "canonical/astra_runtime/missions/PARENT-OPENENDED-HTTP2-FLOW-CONTROL-LIMITS-REAL-TASK-20260930-003.json",
    "git_blob_sha1": "fac316bc6d273bf84e06843a6850d358fd3a2e56"
  },
  {
    "path": "canonical/runtime/astra_runtime.py",
    "git_blob_sha1": "e60345e3814deacc5b79ffd7fcf713febfee0425"
  },
  {
    "path": "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
    "git_blob_sha1": "7badee4878700f2cd4176beb8319d2a6a0bdf782"
  },
  {
    "path": "canonical/runtime/goal_compiler.py",
    "git_blob_sha1": "4b61fe911471854ec15c7900816f61e9e55f602e"
  },
  {
    "path": "canonical/runtime/capability_proposal_generators.py",
    "git_blob_sha1": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2"
  },
  {
    "path": "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
    "git_blob_sha1": "da42f0615380027f963044f80e55ddfa1d73ced1"
  },
  {
    "path": "canonical/runtime/bound_capabilities/broad_objective_decompose.py",
    "git_blob_sha1": "6eb2b20e860da466ad8b793c20060ded1fbf389b"
  },
  {
    "path": "canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py",
    "git_blob_sha1": "816c37742b23739e74a9455a97dd6aea9e767206"
  },
  {
    "path": "canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py",
    "git_blob_sha1": "1dc26e68d18010b66211d1d83f7b2024c8ad1fcf"
  },
  {
    "path": "canonical/runtime/bound_capabilities/objective_relevance_bm25.py",
    "git_blob_sha1": "95d2b6bac6f6ffb5db97526407fcd22cbcc6c790"
  },
  {
    "path": "canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py",
    "git_blob_sha1": "fc45fb583f6aeac91f7c88f918644c38fbc70e34"
  },
  {
    "path": "canonical/runtime/bound_capabilities/open_research_source_frontend.py",
    "git_blob_sha1": "46fe82d74a35d9318a134fb95e1d5cecfc2dd485"
  },
  {
    "path": "canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py",
    "git_blob_sha1": "d66a7eb30774f66160b698d8082947776888293d"
  },
  {
    "path": "canonical/runtime/bound_capabilities/objective_claim_operand_binding.py",
    "git_blob_sha1": "48fd058430d8d361fc75beced567c7b6d1166531"
  },
  {
    "path": "canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py",
    "git_blob_sha1": "6ff13c32704c0b3283c42a51f718e875110a13ca"
  },
  {
    "path": "canonical/runtime/bound_capabilities/source_authority_binding_ror.py",
    "git_blob_sha1": "9396ff7169b274af9bbfbe736e004587631e3b05"
  },
  {
    "path": "canonical/action_intents/2026-09-30_EXECUTE_GUARDED_HTTP2_PARENT_TASK_A_V1.json",
    "git_blob_sha1": "0fd94d0b522053161a99da66265d375da5a3aa6c"
  },
  {
    "path": "execution_guard/github_actions_guarded_run_live.py",
    "git_blob_sha1": "30ea2fd2cc548444477c7b234a59129ff8386235"
  },
  {
    "path": "execution_guard/actions_admission.py",
    "git_blob_sha1": "6c46abef66c036f5382d5792b11a82a289b4dd94"
  },
  {
    "path": "execution_guard/github_ref_store_live.py",
    "git_blob_sha1": "a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
  },
  {
    "path": "run_guarded_http2_parent_task_once.py",
    "git_blob_sha1": "4fc72237ef53aa958805fab81ab5585517e339d9"
  }
],
  "command":["bash","-lc","ASTRA_DISABLE_MODEL_PLANNER=1 python run_guarded_http2_parent_task_once.py"],
  "authority":{
    "brain_pr_freeze":455,
    "brain_pr_lease":458,
    "brain_carrier_prestart_rejection_run":36688442377,
    "brain_carrier_prestart_steps":0,
    "prior_unguarded_pr":456,
    "no_prior_physical_spend":true
  }
}
(ROOT/"guarded_http2_parent_task_a_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
