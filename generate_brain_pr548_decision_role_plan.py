#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256
CAND="canonical/runtime/bound_capabilities/decision_role_relevance_admission.py"
RANK="canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
BINDER="canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"
FOCUS="canonical/runtime/bound_capabilities/research_query_focus.py"
TEST="canonical/tests/test_decision_role_relevance_admission.py"
ORACLE="verify_pr548_decision_role_relevance.py"
AUTH="pr548_decision_role_authority.json"
GOAL=(
 "Independently guard-qualify exact Brain PR548 candidate 9ffe718550a08021ea14c73a22894737be6592cb. "
 "For bounded explicit comparisons, source relevance admission must require the exact core decision property plus at least "
 "one requested operand identity/discriminator, reject high-overlap wrong-property and wrong-operand candidates, select "
 "the highest BM25 candidate that passes the role gate, preserve incumbent behavior outside bounded comparison grammar, "
 "execute no parent task, replay no materials Task C, use no model cognition, and incur zero incremental spend."
)
def sha256(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
  "gate_id":"BRAIN-PR548-DECISION-ROLE-RELEVANCE-QUALIFICATION-20260930-V1",
  "problem_sha256":problem_sha256(GOAL),
  "task_sha256":sha256(ORACLE),
  "runtime_sha256":sha256(CAND),
  "canonical_base":"81f2f813f03b5d80ac2e44080bd19d967bd06463",
  "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
  {"path":CAND,"git_blob_sha1":"4a0d49386c3c1410a09d847fddd9772545ba0095"},
  {"path":RANK,"git_blob_sha1":"0abb5225fe9fba2443f2df46b2e41bd1c7dd7436"},
  {"path":BINDER,"git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
  {"path":FOCUS,"git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
  {"path":TEST,"git_blob_sha1":"2deabf08cad9476afd3467edcf7db5224927488b"},
  {"path":ORACLE,"git_blob_sha1":"f823132a51136cf113149cc95a8ab8709bec7e36"},
  {"path":AUTH,"git_blob_sha1":"238882568021f468a355e7be0e39d333dde544e4"},
  {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
  {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
  {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_decision_role_relevance_admission.py && python verify_pr548_decision_role_relevance.py"
 ],
 "authority":{
  "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION","brain_pr":548,
  "brain_candidate_head":"9ffe718550a08021ea14c73a22894737be6592cb",
  "qualification_only":True,"parent_task_execution":False,"parent_task_replay":False,
  "materials_task_c_replay":False,"model_dependency_count":0,"incremental_spend_usd":0
 }
}
(ROOT/"brain_pr548_decision_role_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],
                  "task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
