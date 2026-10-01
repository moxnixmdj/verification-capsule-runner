#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256
GOAL=("Independently qualify immutable Brain PR548 at exact commit "
      "9ffe718550a08021ea14c73a22894737be6592cb for bounded core decision-property "
      "and requested-operand relevance admission layered over incumbent BM25. "
      "No materials Task C replay, no parent execution.")
PINNED={
"canonical/runtime/bound_capabilities/decision_role_relevance_admission.py":"4a0d49386c3c1410a09d847fddd9772545ba0095",
"canonical/runtime/bound_capabilities/objective_relevance_bm25.py":"0abb5225fe9fba2443f2df46b2e41bd1c7dd7436",
"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py":"48fd058430d8d361fc75beced567c7b6d1166531",
"canonical/runtime/bound_capabilities/research_query_focus.py":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
"canonical/tests/test_decision_role_relevance_admission.py":"2deabf08cad9476afd3467edcf7db5224927488b",
"canonical/action_intents/2026-09-30_REPAIR_DECISION_ROLE_RELEVANCE_ADMISSION_V1.json":"253bfc3c9673da3ebef31779f38ee656055c67a3",
"verify_brain_pr548_decision_role_relevance.py":"68fcd31d12289f831389acff7de366e972819c1b",
"pr548_decision_role_authority.json":"6bcd4917a144be4f267939fd0cb70e3d80cdd68c",
"execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
"execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
"execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
}
def sha256_file(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR548-DECISION-ROLE-RELEVANCE-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256_file("canonical/tests/test_decision_role_relevance_admission.py"),
   "runtime_sha256":sha256_file("canonical/runtime/bound_capabilities/objective_relevance_bm25.py"),
   "canonical_base":"9ffe718550a08021ea14c73a22894737be6592cb",
   "authorization_sha256":sha256_file("pr548_decision_role_authority.json")
 },
 "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in PINNED.items()],
 "command":["bash","-lc",
   "set -euo pipefail; mkdir -p _terminal; "
   "python canonical/tests/test_decision_role_relevance_admission.py 2>&1 | tee _terminal/authored-tests.log; "
   "python verify_brain_pr548_decision_role_relevance.py 2>&1 | tee _terminal/independent-oracle.log"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":548,
   "brain_pr_head":"9ffe718550a08021ea14c73a22894737be6592cb",
   "authoritative_parent_evidence_run":36698638943,
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "spent_materials_task_c_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr548_guarded_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
