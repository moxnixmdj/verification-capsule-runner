#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
GOAL="Independently qualify the exact Brain PR474 corrected broad multi-clause research routing boundary using authored regression tests plus a separate fresh cross-domain oracle, without executing or replaying any parent scientific task."
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR474-CORRECTED-BROAD-ROUTING-QUALIFICATION-20260930-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest(),
   "task_sha256":sha256_file("verify_brain_pr474_independent.py"),
   "runtime_sha256":sha256_file("pr474_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py"),
   "canonical_base":"691b08b7f51adca1ed980df384153b71ef38e046",
   "authorization_sha256":sha256_file("pr474_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py")
 },
 "pinned_files":[
   {"path":"pr474_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py","git_blob_sha1":"1efaec4ba51ecb5c40072b3190853f4de89d8f77"},
   {"path":"pr474_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
   {"path":"pr474_snapshot/canonical/tests/test_broad_objective_semantic_decomposition.py","git_blob_sha1":"2df7c6ec85083458a69675f6ff86eca9c00ea278"},
   {"path":"verify_brain_pr474_independent.py","git_blob_sha1":"a7962066b657c7ccfc94ba97e6eb520dd0bd1b4c"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","cd pr474_snapshot && python canonical/tests/test_broad_objective_semantic_decomposition.py && cd .. && python verify_brain_pr474_independent.py"],
 "authority":{
   "brain_pr":474,
   "brain_pr_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
   "brain_pr_base":"691b08b7f51adca1ed980df384153b71ef38e046",
   "qualification_scope":"NON_PARENT_EXACT_BYTE_GENERIC_ROUTING_REPAIR",
   "parent_task_executed":False,
   "spent_http2_parent_replayed":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"guarded_pr474_broad_routing_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
