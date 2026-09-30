#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE="canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py"
FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
TEST="canonical/tests/test_scholarly_provenance_admission_materialization.py"
GOAL="Independently qualify Brain PR528 generic scholarly provenance admission and selected-source live materialization without executing any parent task."
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR528-SCHOLARLY-ADMISSION-MATERIALIZATION-QUALIFICATION-20260930-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(SOURCE),
   "runtime_sha256":sha256_file(FRONT),
   "canonical_base":"513e350225ff16485d729a8e9a0d74f196a7e103",
   "authorization_sha256":sha256_file(TEST)
 },
 "pinned_files":[
   {"path":SOURCE,"git_blob_sha1":"ba58cb020ab817896362b65e0de9b1fce3de8f50"},
   {"path":FRONT,"git_blob_sha1":"eefe76faacb0c420ccab73db2395742e40ea35f2"},
   {"path":TEST,"git_blob_sha1":"26d2a1e5ea7be3e569011ec732dde0498ea933c8"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","mkdir -p _terminal; set -o pipefail; python canonical/tests/test_scholarly_provenance_admission_materialization.py 2>&1 | tee _terminal/test.log"],
 "authority":{
   "brain_pr":528,
   "brain_pr_head":"513e350225ff16485d729a8e9a0d74f196a7e103",
   "parent_task_execution":False,
   "parent_task_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr528_guarded_qualification_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"source_sha256":plan["frozen"]["task_sha256"],"frontend_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
