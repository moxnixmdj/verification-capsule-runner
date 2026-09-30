#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
BROAD="canonical/runtime/bound_capabilities/broad_objective_decompose.py"
GROUND="canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"
TEST="canonical/tests/test_broad_objective_semantic_decomposition.py"
AUTH="canonical/action_intents/2026-09-30_REPAIR_BROAD_EXPLICIT_RECIPE_FAILCLOSED_V2.json"
ORACLE="qualification/pr496/independent_oracle.py"
GOAL="Independently qualify exact Brain PR496 broad-research explicit-recipe fail-closed repair bytes under adversarial concrete-command and abstract-method-selection cases without executing any parent scientific task."
def s256(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
  "gate_id":"BRAIN-QUALIFY-PR496-BROAD-EXPLICIT-RECIPE-FAILCLOSED-20260930-V1",
  "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
  "task_sha256":s256(TEST),
  "runtime_sha256":s256(BROAD),
  "canonical_base":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
  "authorization_sha256":s256(AUTH)
 },
 "pinned_files":[
  {"path":BROAD,"git_blob_sha1":"3ded762075ed222228a14877af631f1e2e6d9e4c"},
  {"path":GROUND,"git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
  {"path":TEST,"git_blob_sha1":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785"},
  {"path":AUTH,"git_blob_sha1":"6e37f2b04c6a5201362ac162713364dcebf59e6a"},
  {"path":ORACLE,"git_blob_sha1":"c9da0a2a9b81f6a31241769fd7023ae28b2bbc2f"},
  {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
  {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
  {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","python canonical/tests/test_broad_objective_semantic_decomposition.py && python qualification/pr496/independent_oracle.py"],
 "authority":{
  "kind":"NON_PARENT_GUARDED_INDEPENDENT_ADVERSARIAL_QUALIFICATION",
  "brain_pr":496,
  "brain_head_sha":"d472da3082c8a26d16b91aad0997cb369ee5180e",
  "falsification_run":36689999285,
  "parent_task_execution":False,
  "parent_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0
 }
}
(ROOT/"qualification/pr496/guarded_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","frozen":plan["frozen"]},sort_keys=True))
