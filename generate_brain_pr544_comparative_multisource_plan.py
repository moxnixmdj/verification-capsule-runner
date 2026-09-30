#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
BINDER="canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"
REL="canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py"
TEST="canonical/tests/test_comparative_operand_multisource_retrieval.py"
AUTH="pr544_comparative_multisource_authority.json"
GOAL=(
 "Independently guard-qualify frozen Brain PR544 candidate 0d77d4a65dcf0d96d815c8592ac90f8c40cf34b6: "
 "for explicit comparative objectives, derive distinct operand evidence queries using the inherited deterministic "
 "claim/operand parser, route each operand through the existing source pipeline, fail closed if either operand lacks "
 "admissible evidence, merge only provenance-complete verified evidence units, and evaluate the original numeric relation. "
 "No materials Task C replay, no parent task execution, no model cognition, zero incremental spend."
)
def sha256(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR544-COMPARATIVE-OPERAND-MULTISOURCE-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256(TEST),
   "runtime_sha256":sha256(FRONT),
   "canonical_base":"81f2f813f03b5d80ac2e44080bd19d967bd06463",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
   {"path":FRONT,"git_blob_sha1":"f04bbf9182f75ea0b0442e2bc1eca7ce39dcbbfb"},
   {"path":BINDER,"git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
   {"path":REL,"git_blob_sha1":"1da4cca5d8f24892527e496d69d6e0d854220659"},
   {"path":TEST,"git_blob_sha1":"5eaa4473633d88c2b9d6d24dbaf9606429995aea"},
   {"path":AUTH,"git_blob_sha1":"9f15887e53eb981120fe5011073317dd806998ea"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","set -euo pipefail; python canonical/tests/test_comparative_operand_multisource_retrieval.py"],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":544,
   "brain_candidate_head":"0d77d4a65dcf0d96d815c8592ac90f8c40cf34b6",
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "materials_task_c_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr544_comparative_multisource_plan.json").write_text(
 json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],
                  "task_sha256":plan["frozen"]["task_sha256"],
                  "runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
