#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

AUTH="pr496_explicit_recipe_v2_qualification_authorization.json"
BROAD="canonical/runtime/bound_capabilities/broad_objective_decompose.py"
TEST="canonical/tests/test_broad_objective_semantic_decomposition.py"
goal="Independently qualify the exact Brain PR496 explicit-recipe fail-closed v2 bytes against the demonstrated absolute-path false negative, unknown CLI commands, concrete tools attached to generic wording, URLs/save recipes, preserved abstract method wording, and the frozen genomics Task B wording without executing any parent task."
def sha256(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PR496-EXPLICIT-RECIPE-FAILCLOSED-V2-QUALIFICATION-20260930-V1",
    "problem_sha256":problem_sha256(goal),
    "task_sha256":sha256(TEST),
    "runtime_sha256":sha256(BROAD),
    "canonical_base":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
    "authorization_sha256":sha256(AUTH)
  },
  "pinned_files":[
    {"path":BROAD,"git_blob_sha1":"3ded762075ed222228a14877af631f1e2e6d9e4c"},
    {"path":"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
    {"path":TEST,"git_blob_sha1":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785"},
    {"path":"verify_pr496_explicit_recipe_v2.py","git_blob_sha1":"0ba1931f6692a833f73af42ed787dfc6a97df680"},
    {"path":AUTH,"git_blob_sha1":"28e9994eaa0dbc95f9e6642dd106422274ee34d3"},
    {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
    {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
    {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
  ],
  "command":["bash","-lc","python canonical/tests/test_broad_objective_semantic_decomposition.py && python verify_pr496_explicit_recipe_v2.py"],
  "authority":{
    "brain_pr":496,
    "brain_candidate_head":"d472da3082c8a26d16b91aad0997cb369ee5180e",
    "authoritative_red_run":36689999285,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "frozen_genomics_task_execution":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0
  }
}
(ROOT/"pr496_explicit_recipe_v2_qualification_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
