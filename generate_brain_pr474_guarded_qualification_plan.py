#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
BROAD="pr474_candidate/broad_objective_decompose.py"
GROUND="pr474_candidate/plain_goal_bound_grounding.py"
ORACLE="verify_brain_pr474_independent.py"
GOAL="Independently qualify the exact Brain PR474 corrected broad-routing boundary without executing or replaying any parent task."

def sha256_file(rel):
    return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()

norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":GOAL,
  "frozen":{
    "gate_id":"BRAIN-PR474-CORRECTED-BROAD-ROUTING-INDEPENDENT-QUALIFICATION-20260930-V1",
    "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
    "task_sha256":sha256_file(BROAD),
    "runtime_sha256":sha256_file(GROUND),
    "canonical_base":"2b2ad1272c28229b3a26fc48f3515138313fd774",
    "authorization_sha256":sha256_file(ORACLE)
  },
  "pinned_files":[
    {"path":BROAD,"git_blob_sha1":"1efaec4ba51ecb5c40072b3190853f4de89d8f77"},
    {"path":GROUND,"git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
    {"path":ORACLE,"git_blob_sha1":"4676d4991f24c3562a8bb9395c730324c5b173ec"},
    {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
    {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
    {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
  ],
  "command":["python","verify_brain_pr474_independent.py"],
  "authority":{
    "brain_pr":474,
    "brain_pr_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
    "parent_task_execution":False,
    "parent_task_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0
  }
}
(ROOT/"brain_pr474_guarded_qualification_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
