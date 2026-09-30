#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
CAND_A="pr474_candidate/broad_objective_decompose.py"
CAND_B="pr474_candidate/plain_goal_bound_grounding.py"
ORACLE="verify_brain_pr474_independent.py"
GOAL="Independently qualify the exact Brain PR474 corrected broad multi-clause research routing boundary without executing or replaying any parent task."
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR474-BROAD-ROUTING-INDEPENDENT-QUALIFICATION-20260930-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(CAND_A),
   "runtime_sha256":sha256_file(CAND_B),
   "canonical_base":"691b08b7f51adca1ed980df384153b71ef38e046",
   "authorization_sha256":sha256_file(ORACLE)
 },
 "pinned_files":[
   {"path":CAND_A,"git_blob_sha1":"1efaec4ba51ecb5c40072b3190853f4de89d8f77"},
   {"path":CAND_B,"git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
   {"path":ORACLE,"git_blob_sha1":"a7962066b657c7ccfc94ba97e6eb520dd0bd1b4c"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["python","verify_brain_pr474_independent.py"],
 "authority":{
   "brain_pr":474,
   "brain_pr_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
   "brain_base":"691b08b7f51adca1ed980df384153b71ef38e046",
   "qualification_only":True,
   "parent_task_execution":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr474_guarded_qualification_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"candidate_a_sha256":plan["frozen"]["task_sha256"],"candidate_b_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
