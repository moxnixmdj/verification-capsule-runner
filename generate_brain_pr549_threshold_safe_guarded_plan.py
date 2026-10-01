#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

GOAL=(
  "Independently qualify immutable Brain PR549 at exact commit "
  "85a572980596f50c18ea6645b0a72b3681185c14 for deterministic decision-property "
  "and operand-role source relevance admission, while preserving incumbent behavior "
  "for literal numeric-threshold and unsupported objective shapes. No parent execution or replay."
)

PINS={
"canonical/runtime/bound_capabilities/decision_role_relevance_admission.py":"3036734a9f63945a7b76a5ca7cac86618fbc3677",
"canonical/runtime/bound_capabilities/objective_relevance_bm25.py":"0abb5225fe9fba2443f2df46b2e41bd1c7dd7436",
"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py":"48fd058430d8d361fc75beced567c7b6d1166531",
"canonical/runtime/bound_capabilities/research_query_focus.py":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
"canonical/tests/test_decision_role_relevance_admission.py":"dcfd4bf6da7a7ef01d1f21dff541d9b79b3c8f26",
"canonical/tests/test_objective_relevance_bm25.py":"a4736194a063d05d60f0fc3ca13314956cb5e3de",
"canonical/action_intents/2026-09-30_REPAIR_DECISION_ROLE_RELEVANCE_ADMISSION_V1.json":"89e485d65d7bc8e9ddd3e76df36c3b2dc78b1d12",
"verify_brain_pr549_threshold_safe_decision_role.py":"79fa38f63d8757b7d9b5f2ba7369d6765ba678c9",
"pr549_threshold_safe_authority.json":"3d484b2d6107eea9850493b79b07f9f2e54b0fb1",
"execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
"execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
"execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
}

def sha256_file(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":GOAL,
  "frozen":{
    "gate_id":"BRAIN-PR549-THRESHOLD-SAFE-DECISION-ROLE-QUALIFICATION-20260930-V1",
    "problem_sha256":problem_sha256(GOAL),
    "task_sha256":sha256_file("canonical/tests/test_decision_role_relevance_admission.py"),
    "runtime_sha256":sha256_file("canonical/runtime/bound_capabilities/objective_relevance_bm25.py"),
    "canonical_base":"85a572980596f50c18ea6645b0a72b3681185c14",
    "authorization_sha256":sha256_file("pr549_threshold_safe_authority.json")
  },
  "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in PINS.items()],
  "command":["bash","-lc",
    "set -euo pipefail; mkdir -p _terminal; "
    "python canonical/tests/test_objective_relevance_bm25.py 2>&1 | tee _terminal/inherited-bm25.log; "
    "python canonical/tests/test_decision_role_relevance_admission.py 2>&1 | tee _terminal/authored-role.log; "
    "python verify_brain_pr549_threshold_safe_decision_role.py 2>&1 | tee _terminal/independent-oracle.log"
  ],
  "authority":{
    "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
    "brain_pr":549,
    "brain_pr_head":"85a572980596f50c18ea6645b0a72b3681185c14",
    "qualification_only":True,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "materials_task_c_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0
  }
}
(ROOT/"brain_pr549_threshold_safe_guarded_plan.json").write_text(
  json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
