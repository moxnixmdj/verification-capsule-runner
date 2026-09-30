#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
PROV="canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py"
TEST="canonical/tests/test_scholarly_provenance_admission_materialization.py"
INTENT="canonical/action_intents/2026-09-30_REPAIR_METADATA_REFINED_PROVENANCE_PRESERVATION_V1.json"
AUTH="pr537_refined_provenance_authority.json"
ORACLE="verify_brain_pr537_refined_provenance.py"
GOAL=(
 "Independently qualify frozen Brain PR537 commit 2c4f2d9bc02d07dcd61d7fc6d01f38c679941813: "
 "the single metadata-refined fallback preserves every provenance-verified candidate class through deterministic "
 "relevance; a refined bibliographic winner is live-materialized only after selection using the existing "
 "identity-bound materializer; a refined live winner is not redundantly materialized; failed selected "
 "materialization remains fail-closed; exactly one refinement is allowed; no parent task is executed or replayed."
)
def sha256(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR537-REFINED-PROVENANCE-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256(TEST),
   "runtime_sha256":sha256(FRONT),
   "canonical_base":"71fbeb1e21683a165066c23b211781eee8fab61b",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
   {"path":PROV,"git_blob_sha1":"8f6f80403dc48268ecbf244ae633ea2928204148"},
   {"path":FRONT,"git_blob_sha1":"96c63f6586df27a2bf2f508f1f83215676cdd4c8"},
   {"path":TEST,"git_blob_sha1":"f574fe6c9b7444b4938677b00e3ccbb9c485b58d"},
   {"path":INTENT,"git_blob_sha1":"06e1c53a108e6b58f5d9231475f6eeb2701b3268"},
   {"path":AUTH,"git_blob_sha1":"1aa3068e9517322edf75faca1135debb8fe141ee"},
   {"path":ORACLE,"git_blob_sha1":"683a47746a40b10653d4ddd494b85d4345f6a34d"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_scholarly_provenance_admission_materialization.py && "
   "python verify_brain_pr537_refined_provenance.py"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":537,
   "brain_candidate_head":"2c4f2d9bc02d07dcd61d7fc6d01f38c679941813",
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "materials_task_c_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr537_refined_provenance_plan.json").write_text(
 json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],
                  "task_sha256":plan["frozen"]["task_sha256"],
                  "runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
