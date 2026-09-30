#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256
AUTH="pr546_decision_role_relevance_authority.json"
ORACLE="verify_brain_pr546_decision_role_relevance.py"
FILES={
 "canonical/runtime/bound_capabilities/objective_relevance_bm25.py":"d603a2ec6ff1706a07ec9acdf47b1e61095d46a3",
 "canonical/tests/test_objective_relevance_bm25.py":"29d2bf47a6d557c668d41605dfaf94a7543eccb1",
 "canonical/runtime/bound_capabilities/objective_claim_operand_binding.py":"48fd058430d8d361fc75beced567c7b6d1166531",
 "canonical/runtime/bound_capabilities/research_query_focus.py":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
 AUTH:"b9e791eb91e34be265cde18469488be84a6c4a45",
 ORACLE:"60f511889dbc6675a7187ec9542579ad44a399e0",
 "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
 "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
 "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
}
def sha256(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
GOAL=(
 "Independently qualify frozen Brain PR546 candidate d6431d5522c295a6ce54468280d3941182ea05aa: "
 "bounded model-independent decision-property and operand-role relevance admission composed with existing BM25 and "
 "the already-qualified objective relation parser. Reproduce the materials Task-C decoy/correct-source distinction, "
 "cross-domain role cases, exact discriminator failures, fail-closed unresolved roles, and non-relation backward compatibility. "
 "No parent task execution or Task-C replay."
)
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR546-DECISION-ROLE-RELEVANCE-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256("canonical/tests/test_objective_relevance_bm25.py"),
   "runtime_sha256":sha256("canonical/runtime/bound_capabilities/objective_relevance_bm25.py"),
   "canonical_base":"81f2f813f03b5d80ac2e44080bd19d967bd06463",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in FILES.items()],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_objective_relevance_bm25.py && "
   "python verify_brain_pr546_decision_role_relevance.py"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":546,
   "brain_candidate_head":"d6431d5522c295a6ce54468280d3941182ea05aa",
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "spent_materials_task_c_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr546_decision_role_relevance_plan.json").write_text(
 json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
