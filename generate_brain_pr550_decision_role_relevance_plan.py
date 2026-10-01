#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256
AUTH="pr550_decision_role_relevance_authority.json"
ORACLE="verify_brain_pr550_decision_role_relevance.py"
FILES={
  "canonical/runtime/bound_capabilities/decision_role_relevance_admission.py": "dbaf728d40569746da985e623af152ed55be42bf",
  "canonical/runtime/bound_capabilities/objective_relevance_bm25.py": "0abb5225fe9fba2443f2df46b2e41bd1c7dd7436",
  "canonical/tests/test_decision_role_relevance_admission.py": "dcfd4bf6da7a7ef01d1f21dff541d9b79b3c8f26",
  "canonical/runtime/bound_capabilities/objective_claim_operand_binding.py": "48fd058430d8d361fc75beced567c7b6d1166531",
  "canonical/runtime/bound_capabilities/research_query_focus.py": "5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
  "canonical/tests/test_objective_relevance_bm25.py": "a4736194a063d05d60f0fc3ca13314956cb5e3de"
}
FILES.update({
 AUTH:"5b49159724aaeb0e1f4a38fcf8670379b3b842c0",
 ORACLE:"831155d57e9dd95ad43ead0e8e1a642f89ffeab4",
 "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
 "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
 "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
})
def sha256(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
GOAL=(
 "Independently qualify exact Brain PR550 candidate 3b8ab760e12c1cac8949240ebf8e15ec94937121: threshold-safe bounded decision-property "
 "and operand-role relevance admission over incumbent BM25, including Task-C causal shape, cross-domain role "
 "cases, hard identifiers, protocol identifiers, numeric-threshold compatibility, broad-objective backward "
 "compatibility, and zero model cognition. No parent execution and no Task-C replay."
)
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
  "gate_id":"BRAIN-PR550-THRESHOLD-SAFE-DECISION-ROLE-QUALIFICATION-20260930-V2",
  "problem_sha256":problem_sha256(GOAL),
  "task_sha256":sha256("canonical/tests/test_decision_role_relevance_admission.py"),
  "runtime_sha256":sha256("canonical/runtime/bound_capabilities/decision_role_relevance_admission.py"),
  "canonical_base":"81f2f813f03b5d80ac2e44080bd19d967bd06463",
  "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in FILES.items()],
 "command":["bash","-lc",
   "set -euo pipefail; "
   "python canonical/tests/test_decision_role_relevance_admission.py && "
   "python canonical/tests/test_objective_relevance_bm25.py && "
   "python verify_brain_pr550_decision_role_relevance.py"
 ],
 "authority":{
  "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
  "brain_pr":550,"brain_candidate_head":"3b8ab760e12c1cac8949240ebf8e15ec94937121",
  "qualification_only":True,"parent_task_execution":False,"parent_task_replay":False,
  "spent_materials_task_c_replay":False,"model_dependency_count":0,"incremental_spend_usd":0
 }
}
(ROOT/"brain_pr550_decision_role_relevance_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
