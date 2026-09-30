#!/usr/bin/env python3
import hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

GOAL=("Independently qualify Brain PR496 exact explicit-recipe fail-closed repair with the complete "
      "current Brain grounding dependency closure. Legitimate abstract verification-method language "
      "and the frozen genomics Task B goal must remain broad-research admissible; absolute executable "
      "paths, unknown CLI commands, scripts, URLs, and generic-method wording with a concrete tool "
      "must fail closed. This is a corrected non-parent qualifier after run 36690944162 used stale "
      "runner grounding bytes. No parent task execution or replay.")

def sha256(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":GOAL,
  "frozen":{
    "gate_id":"BRAIN-PR496-EXPLICIT-RECIPE-FAILCLOSED-QUALIFICATION-COMPLETE-CLOSURE-20260930-V2",
    "problem_sha256":problem_sha256(GOAL),
    "task_sha256":sha256("canonical/tests/test_broad_objective_semantic_decomposition.py"),
    "runtime_sha256":sha256("canonical/runtime/bound_capabilities/broad_objective_decompose.py"),
    "canonical_base":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
    "authorization_sha256":sha256("pr496_explicit_recipe_qualification_authorization_v2.json")
  },
  "pinned_files":[
    {"path":"canonical/runtime/bound_capabilities/broad_objective_decompose.py","git_blob_sha1":"3ded762075ed222228a14877af631f1e2e6d9e4c"},
    {"path":"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
    {"path":"canonical/tests/test_broad_objective_semantic_decomposition.py","git_blob_sha1":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785"},
    {"path":"verify_pr496_explicit_recipe_residual.py","git_blob_sha1":"64c60f3967444a5e2520c27a65f67e87cd375202"},
    {"path":"pr496_explicit_recipe_qualification_authorization_v2.json","git_blob_sha1":"71d65f58458f1393391a48c90d8ac9bf17ae0779"},
    {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
    {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
    {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
  ],
  "command":["bash","-lc","python canonical/tests/test_broad_objective_semantic_decomposition.py && python verify_pr496_explicit_recipe_residual.py"],
  "authority":{
    "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
    "brain_pr":496,
    "falsification_run_id":36689999285,
    "invalid_prior_qualifier_run_id":36690944162,
    "parent_task_execution":False,
    "parent_task_replay":False
  }
}
(ROOT/"guarded_pr496_explicit_recipe_residual_plan_v2.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"],"authorization_sha256":plan["frozen"]["authorization_sha256"]},sort_keys=True))
