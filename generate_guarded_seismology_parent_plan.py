#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
TASK="brain_snapshot/canonical/tasks/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
MISSION="brain_snapshot/canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
RUNTIME="brain_snapshot/canonical/runtime/astra_runtime.py"
AUTH="brain_snapshot/canonical/action_intents/2026-09-30_EXECUTE_GUARDED_SEISMOLOGY_TASK_B_V2.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-PARENT-OPENENDED-SEISMOLOGY-KAMCHATKA-TSUNAMI-20260930-002-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(TASK),
   "runtime_sha256":sha256_file(RUNTIME),
   "canonical_base":"89e91fc0bca9f099a728e7b6c19c1cefd97102ce",
   "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
   {"path":TASK,"git_blob_sha1":"39ed2897a377914876afb97e2bb0d5cb9f3036a8"},
   {"path":MISSION,"git_blob_sha1":"7063dd27d58104a0b3e29d54170ac6b816d9bb2f"},
   {"path":RUNTIME,"git_blob_sha1":"426ffe58e405dc4f1ba2eb4e838e03a1df771964"},
   {"path":"brain_snapshot/canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","git_blob_sha1":"7badee4878700f2cd4176beb8319d2a6a0bdf782"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py","git_blob_sha1":"3ded762075ed222228a14877af631f1e2e6d9e4c"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/open_research_source_frontend.py","git_blob_sha1":"1ec11496aa84f261fc2c7e8e689ba687581d8b3c"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py","git_blob_sha1":"d66a7eb30774f66160b698d8082947776888293d"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py","git_blob_sha1":"045369d8cba5680c60b57e834d09d12a54d94380"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/objective_relevance_bm25.py","git_blob_sha1":"a25a34d879413a9853f1d1ffd8ef5e4f6bdd2245"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/research_query_focus.py","git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
   {"path":AUTH,"git_blob_sha1":"c85401a6905b79c5f9b4a3020f1d1be11ecc426c"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","set -uo pipefail; mkdir -p _terminal; cd brain_snapshot; set +e; ASTRA_DISABLE_MODEL_PLANNER=1 python canonical/runtime/astra_runtime.py canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json 2>&1 | tee ../_terminal/producer.log; code=${PIPESTATUS[0]}; printf '%s\\n' \"$code\" > ../_terminal/producer_exit_code.txt; exit \"$code\""],
 "authority":{
   "brain_freeze_pr":515,
   "brain_execution_lease_pr":517,
   "brain_base_commit":"89e91fc0bca9f099a728e7b6c19c1cefd97102ce",
   "task_id":"PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002",
   "freshness_identity":"TASK_CONTENT_AND_PROBLEM_HASH__UNEXECUTED_BEFORE_THIS_GATE",
   "no_same_task_replay":True,
   "parent_phase_label":"TASK_B_LEGACY_LABEL__NEXT_FRESH_PARENT_ATTEMPT_AFTER_SPENT_GENOMICS",
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"guarded_seismology_parent_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
