#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
TEST="canonical/tests/test_scholarly_provenance_admission_materialization.py"
ORACLE="verify_pr537_provenance_preservation.py"
AUTH="canonical/action_intents/2026-09-30_REPAIR_METADATA_REFINED_PROVENANCE_PRESERVATION_V1.json"
PLAN="guarded_pr537_provenance_preservation_plan.json"

def sha256_file(rel):
    return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()

goal="Requalify the complete exact Brain PR537 metadata-refined provenance-class preservation closure, including the exact provenance materializer dependency, without executing or replaying any parent scientific task."
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem_sha256=hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest()

plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-PR537-METADATA-REFINED-PROVENANCE-PRESERVATION-20260930-V2",
   "problem_sha256":problem_sha256,
   "task_sha256":sha256_file(ORACLE),
   "runtime_sha256":sha256_file(FRONT),
   "canonical_base":"2c4f2d9bc02d07dcd61d7fc6d01f38c679941813",
   "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
   {"path":FRONT,"git_blob_sha1":"96c63f6586df27a2bf2f508f1f83215676cdd4c8"},
   {"path":TEST,"git_blob_sha1":"f574fe6c9b7444b4938677b00e3ccbb9c485b58d"},
   {"path":ORACLE,"git_blob_sha1":"0ebbb3279e5419b87e52da75b520c7e412a79d44"},
   {"path":AUTH,"git_blob_sha1":"06e1c53a108e6b58f5d9231475f6eeb2701b3268"},
   {"path":"canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py","git_blob_sha1":"8f6f80403dc48268ecbf244ae633ea2928204148"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","python canonical/tests/test_scholarly_provenance_admission_materialization.py && python verify_pr537_provenance_preservation.py"],
 "authority":{
   "brain_pr":537,
   "brain_pr_head":"2c4f2d9bc02d07dcd61d7fc6d01f38c679941813",
   "parent_task_execution":False,
   "materials_task_replay":False
 }
}
(ROOT/PLAN).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":problem_sha256},sort_keys=True))
