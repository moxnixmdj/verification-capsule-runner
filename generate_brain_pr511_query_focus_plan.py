#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
SRC="canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"
TEST="canonical/tests/test_open_web_source_candidate_discovery.py"
AUTH="pr511_query_focus_authority.json"
ORACLE="verify_brain_pr511_query_focus.py"
def sha256_file(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
goal="Qualify Brain PR511 generic open-research decision-clause query focus with exact bytes, authored regressions, independent adversarial cases, and fresh non-parent live search evidence."
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-PR511-QUERY-FOCUS-QUALIFICATION-20260930-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(TEST),
   "runtime_sha256":sha256_file(SRC),
   "canonical_base":"0d795dad885e706e6eb1cfd4d20cd2b2edd5cf12",
   "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
   {"path":SRC,"git_blob_sha1":"a3ae22718c82569fdc954f979cb347189d6edfcd"},
   {"path":TEST,"git_blob_sha1":"d93e1c3a4b689884a10c474d049bd1e4aad830a2"},
   {"path":AUTH,"git_blob_sha1":"ee9bf174610d94bed1fd3c70293e1a4db160acec"},
   {"path":ORACLE,"git_blob_sha1":"6fc007d25beff20f62a0508b28e1a837266d185f"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","set -euo pipefail; python canonical/tests/test_open_web_source_candidate_discovery.py; python verify_brain_pr511_query_focus.py"],
 "authority":{"brain_pr":511,"qualification_only":True,"parent_task_executed":False,"model_dependency_count":0,"incremental_spend_usd":0}
}
(ROOT/"brain_pr511_query_focus_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
