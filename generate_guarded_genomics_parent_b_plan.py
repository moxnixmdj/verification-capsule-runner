#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
TASK="brain_snapshot/canonical/tasks/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
MISSION="brain_snapshot/canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
RUNTIME="brain_snapshot/canonical/runtime/astra_runtime.py"
AUTH="brain_snapshot/canonical/action_intents/2026-09-30_FREEZE_FRESH_GENOMICS_REFERENCE_LENGTH_OPENENDED_PARENT_TASK_A_V1.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-TASK-B-20260930-005-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(TASK),
   "runtime_sha256":sha256_file(RUNTIME),
   "canonical_base":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
   "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":[
   {"path":TASK,"git_blob_sha1":"5f1a8fea0d29c2a60dcc7a038ecd557829e602e7"},
   {"path":MISSION,"git_blob_sha1":"03e718a9c779c26d26e7af140f2f65549c1a7f6e"},
   {"path":RUNTIME,"git_blob_sha1":"426ffe58e405dc4f1ba2eb4e838e03a1df771964"},
   {"path":"brain_snapshot/canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","git_blob_sha1":"7badee4878700f2cd4176beb8319d2a6a0bdf782"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py","git_blob_sha1":"1efaec4ba51ecb5c40072b3190853f4de89d8f77"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/open_research_source_frontend.py","git_blob_sha1":"1ec11496aa84f261fc2c7e8e689ba687581d8b3c"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","git_blob_sha1":"46e8e7466479ea298c34e5fa682d49c374510ce9"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/objective_claim_operand_binding.py","git_blob_sha1":"48fd058430d8d361fc75beced567c7b6d1166531"},
   {"path":"brain_snapshot/canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py","git_blob_sha1":"d66a7eb30774f66160b698d8082947776888293d"},
   {"path":AUTH,"git_blob_sha1":"58bfad63b66a3ec900146951acf8dfcb9368d7d0"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc","set -uo pipefail; mkdir -p _terminal; cd brain_snapshot; set +e; ASTRA_DISABLE_MODEL_PLANNER=1 python canonical/runtime/astra_runtime.py canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json 2>&1 | tee ../_terminal/producer.log; code=${PIPESTATUS[0]}; printf '%s\\n' \"$code\" > ../_terminal/producer_exit_code.txt; exit \"$code\""],
 "authority":{
   "brain_freeze_pr":478,
   "brain_correction_pr":490,
   "brain_base_commit":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
   "task_id":"PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005",
   "no_same_task_replay":True,
   "parent_phase":"TASK_B",
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"guarded_genomics_parent_b_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
