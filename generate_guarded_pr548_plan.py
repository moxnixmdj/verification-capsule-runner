#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
ROLE="canonical/runtime/bound_capabilities/decision_role_relevance_admission.py"
RANK="canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
TEST="canonical/tests/test_decision_role_relevance_admission.py"
ORACLE="verify_pr548_core_property_relevance.py"
AUTH="canonical/action_intents/2026-09-30_REPAIR_DECISION_ROLE_RELEVANCE_ADMISSION_V1.json"
PLAN="guarded_pr548_core_property_relevance_plan.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
goal="Independently qualify immutable Brain PR548 core-property and operand-discriminator relevance admission without executing or replaying any parent scientific task."
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem=hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
  "gate_id":"BRAIN-PR548-CORE-PROPERTY-DECISION-ROLE-RELEVANCE-20260930-V1",
  "problem_sha256":problem,
  "task_sha256":sha256_file(ORACLE),
  "runtime_sha256":sha256_file(RANK),
  "canonical_base":"9ffe718550a08021ea14c73a22894737be6592cb",
  "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
  {"path":ROLE,"git_blob_sha1":"4a0d49386c3c1410a09d847fddd9772545ba0095"},
  {"path":RANK,"git_blob_sha1":"0abb5225fe9fba2443f2df46b2e41bd1c7dd7436"},
  {"path":"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
  {"path":"canonical/runtime/bound_capabilities/research_query_focus.py","git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
  {"path":TEST,"git_blob_sha1":"2deabf08cad9476afd3467edcf7db5224927488b"},
  {"path":ORACLE,"git_blob_sha1":"027e33eacd67534d51110334754a4e14af58db00"},
  {"path":AUTH,"git_blob_sha1":"253bfc3c9673da3ebef31779f38ee656055c67a3"},
  {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
  {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
  {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","python canonical/tests/test_decision_role_relevance_admission.py && python verify_pr548_core_property_relevance.py"],
 "authority":{"brain_pr":548,"immutable_head":"9ffe718550a08021ea14c73a22894737be6592cb","parent_task_execution":False,"materials_task_replay":False}
}
(ROOT/PLAN).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":problem},sort_keys=True))
