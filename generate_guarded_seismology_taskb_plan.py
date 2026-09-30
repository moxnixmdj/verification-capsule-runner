#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
MISSION="canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
RUNTIME="canonical/runtime/astra_runtime.py"
AUTH="canonical/action_intents/2026-09-30_EXECUTE_GUARDED_SEISMOLOGY_TASK_B_V2.json"
FREEZE="canonical/action_intents/2026-09-30_FREEZE_FRESH_SEISMOLOGY_TASK_B_V2.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
pins=[]
for p in sorted((ROOT/"canonical/runtime").rglob("*")):
    if p.is_file():
        pins.append({"path":str(p.relative_to(ROOT)).replace("\\","/"),"git_blob_sha1":blob_sha(p)})
for rel in [TASK,MISSION,AUTH,FREEZE,"execution_guard/github_actions_guarded_run_live.py","execution_guard/actions_admission.py","execution_guard/github_ref_store_live.py"]:
    p=ROOT/rel
    pins.append({"path":rel,"git_blob_sha1":blob_sha(p)})
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-TASK-B-20260930-002-V1",
   "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
   "task_sha256":sha256_file(TASK),
   "runtime_sha256":sha256_file(RUNTIME),
   "canonical_base":"9c9366e2bc0ee63860007fe17041ec8d8503648f",
   "authorization_sha256":sha256_file(AUTH)
 },
 "pinned_files":pins,
 "command":["bash","-lc","set -uo pipefail; mkdir -p _terminal; set +e; ASTRA_DISABLE_MODEL_PLANNER=1 python canonical/runtime/astra_runtime.py canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json 2>&1 | tee _terminal/producer.log; code=${PIPESTATUS[0]}; printf '%s\\\\n' \\\"$code\\\" > _terminal/producer_exit_code.txt; exit \\\"$code\\\""],
 "authority":{
   "brain_freeze_pr":515,
   "brain_execution_pr":517,
   "brain_execution_merge_commit":"89e91fc0bca9f099a728e7b6c19c1cefd97102ce",
   "brain_authorization_base":"9c9366e2bc0ee63860007fe17041ec8d8503648f",
   "task_id":"PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002",
   "task_git_blob_sha1":"39ed2897a377914876afb97e2bb0d5cb9f3036a8",
   "mission_git_blob_sha1":"7063dd27d58104a0b3e29d54170ac6b816d9bb2f",
   "authorization_git_blob_sha1":"c85401a6905b79c5f9b4a3020f1d1be11ecc426c",
   "no_same_task_replay":True,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"guarded_seismology_taskb_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","pins":len(pins),"problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"]},sort_keys=True))
