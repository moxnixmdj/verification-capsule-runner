#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
CAND="canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
TEST="canonical/tests/test_objective_relevance_bm25.py"
ORACLE="verify_pr545_decision_role_relevance.py"
AUTH="canonical/action_intents/2026-09-30_REPAIR_DECISION_ROLE_RELEVANCE_OPERAND_COVERAGE_V1.json"
PLAN="guarded_pr545_decision_role_relevance_plan.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
goal="Independently qualify exact Brain PR545 decision-role relevance and operand-coverage admission without executing or replaying any parent scientific task."
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem=hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
  "gate_id":"BRAIN-PR545-DECISION-ROLE-RELEVANCE-20260930-V1",
  "problem_sha256":problem,
  "task_sha256":sha256_file(ORACLE),
  "runtime_sha256":sha256_file(CAND),
  "canonical_base":"8845f8262a8bd236cd34f0596ee6ff25546903f4",
  "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
  {"path":CAND,"git_blob_sha1":"62c39a7076f0e5ab8c916d4ff93ce02f8c90149d"},
  {"path":"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
  {"path":"canonical/runtime/bound_capabilities/research_query_focus.py","git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
  {"path":TEST,"git_blob_sha1":"47503616cef0fa5e05caeadd3dfc0815b40d4832"},
  {"path":ORACLE,"git_blob_sha1":"6782912951e05b1184c15c384b33a773c687b7c6"},
  {"path":AUTH,"git_blob_sha1":"5d3b27c477cb4e41d31f54ebda2bb3340171eb8a"},
  {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
  {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
  {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","python canonical/tests/test_objective_relevance_bm25.py && python verify_pr545_decision_role_relevance.py"],
 "authority":{"brain_pr":545,"parent_task_execution":False,"materials_task_replay":False}
}
(ROOT/PLAN).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":problem},sort_keys=True))
