#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-MATERIALS-THERMAL-CONDUCTIVITY-OPEN-RESEARCH-TASK-C-20260930-003.json"
MISSION="canonical/astra_runtime/missions/PARENT-MATERIALS-THERMAL-CONDUCTIVITY-OPEN-RESEARCH-TASK-C-20260930-003.json"
RUNTIME="canonical/runtime/astra_runtime.py"
AUTH="canonical/action_intents/2026-09-30_EXECUTE_GUARDED_MATERIALS_TASK_C_V1.json"
PLAN="guarded_materials_parent_task_c_plan.json"

def sha256_file(rel):
    return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()

mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem_sha256=hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PARENT-MATERIALS-THERMAL-CONDUCTIVITY-20260930-003-V1",
    "problem_sha256":problem_sha256,
    "task_sha256":sha256_file(TASK),
    "runtime_sha256":sha256_file(RUNTIME),
    "canonical_base":"2c023134d9b492d41a474eea8244a4da4cd71c80",
    "authorization_sha256":sha256_file(AUTH)
  },
  "pinned_files":[
    {"path":TASK,"git_blob_sha1":"592732d21f72c1344b82640f99fb50c9ea6ece78"},
    {"path":MISSION,"git_blob_sha1":"320dcbd3515883a9dc7036b7193497fffa2a564d"},
    {"path":RUNTIME,"git_blob_sha1":"426ffe58e405dc4f1ba2eb4e838e03a1df771964"},
    {"path":AUTH,"git_blob_sha1":"735d0cd5f794940ec717158c9cab619199074d45"},
    {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
    {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
    {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"},
    {"path":"run_guarded_materials_parent_task_c_once.py","git_blob_sha1":"1d67ab506bcecfd886d6d13765c5ce49583a44e7"}
  ],
  "command":["bash","-lc","ASTRA_DISABLE_MODEL_PLANNER=1 python run_guarded_materials_parent_task_c_once.py"],
  "authority":{
    "brain_authorization_commit":"5bccb9484a34d43f7f9bb24d7f9cd9ac996e8e83",
    "brain_action_intent":AUTH,
    "prior_execution_count":0,
    "replay_allowed":False
  }
}
(ROOT/PLAN).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({
 "status":"PLAN_GENERATED",
 "problem_sha256":problem_sha256,
 "task_sha256":plan["frozen"]["task_sha256"],
 "runtime_sha256":plan["frozen"]["runtime_sha256"],
 "authorization_sha256":plan["frozen"]["authorization_sha256"]
},sort_keys=True))
