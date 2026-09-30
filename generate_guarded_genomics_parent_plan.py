#!/usr/bin/env python3
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
TASK="canonical/tasks/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
MISSION="canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
AUTH="canonical/action_intents/2026-09-30_EXECUTE_GUARDED_GENOMICS_PARENT_TASK_B_V2.json"
HARNESS="run_guarded_genomics_parent_task_once.py"
GENERATOR="generate_guarded_genomics_parent_plan.py"
GUARD_FILES=[
  "execution_guard/github_actions_guarded_run_live.py",
  "execution_guard/actions_admission.py",
  "execution_guard/github_ref_store_live.py",
]
CANONICAL_BASE="b8a0102421e68f4137a4c5fe72d27ed96fb448b2"

def sha256_file(rel):
    return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()

def blob_sha(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def runtime_paths():
    root=ROOT/"canonical/runtime"
    out=[]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel=p.relative_to(ROOT).as_posix()
        if "__pycache__" in p.parts or p.suffix in {".pyc",".pyo"}:
            continue
        out.append(rel)
    return sorted(out)

mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
task=json.loads((ROOT/TASK).read_text(encoding="utf-8"))
auth=json.loads((ROOT/AUTH).read_text(encoding="utf-8"))
goal=str(mission["goal"])
if task.get("goal_text")!=goal:
    raise RuntimeError("TASK_MISSION_GOAL_MISMATCH")
if mission.get("constraints",{}).get("source_task_blob_sha")!=blob_sha(TASK):
    raise RuntimeError("MISSION_TASK_BLOB_BINDING_MISMATCH")
if auth.get("task_blob_sha")!=blob_sha(TASK):
    raise RuntimeError("AUTH_TASK_BLOB_BINDING_MISMATCH")
if auth.get("canonical_base_commit")!=CANONICAL_BASE:
    raise RuntimeError("AUTH_CANONICAL_BASE_MISMATCH")
if task.get("freshness_class")!="FRESH_GENUINELY_OPEN_ENDED_PARENT_TASK_B":
    raise RuntimeError("TASK_B_FRESHNESS_CLASS_REQUIRED")
if auth.get("parent_task_replay") is not False:
    raise RuntimeError("REPLAY_MUST_BE_FALSE")

norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
runtime_files=runtime_paths()
explicit=[TASK,MISSION,AUTH,HARNESS,GENERATOR]+GUARD_FILES
all_pins=runtime_files+[p for p in explicit if p not in runtime_files]
pins=[{"path":p,"git_blob_sha1":blob_sha(p)} for p in all_pins]
runtime_manifest="\n".join(p+"="+blob_sha(p) for p in runtime_files)
runtime_sha=hashlib.sha256(("runtime-manifest-v1\0"+runtime_manifest).encode()).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-20260930-005-TASK-B-V1",
    "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
    "task_sha256":sha256_file(TASK),
    "runtime_sha256":runtime_sha,
    "canonical_base":CANONICAL_BASE,
    "authorization_sha256":sha256_file(AUTH)
  },
  "pinned_files":pins,
  "command":["bash","-lc","ASTRA_DISABLE_MODEL_PLANNER=1 python run_guarded_genomics_parent_task_once.py"],
  "authority":{
    "brain_freeze_pr":478,
    "brain_bookkeeping_pr":490,
    "brain_execution_lease_pr":497,
    "brain_execution_lease_merge":"781d672f01533b71f6c46d729eec1d74aa6e20d8",
    "prior_spent_http2_run":36688193204,
    "parent_task_execution":True,
    "parent_task_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0
  }
}
(ROOT/"guarded_genomics_parent_task_b_plan.json").write_text(
    json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps({
  "status":"PLAN_GENERATED",
  "problem_sha256":plan["frozen"]["problem_sha256"],
  "task_sha256":plan["frozen"]["task_sha256"],
  "runtime_sha256":plan["frozen"]["runtime_sha256"],
  "pin_count":len(pins)
},sort_keys=True))
