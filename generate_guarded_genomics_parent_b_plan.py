#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
SNAP=ROOT/"brain_snapshot"
MANIFEST=ROOT/"genomics_parent_b_runtime_manifest.json"
TASK="brain_snapshot/canonical/tasks/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
MISSION="brain_snapshot/canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json"
AUTH="brain_snapshot/canonical/action_intents/2026-09-30_EXECUTE_GUARDED_GENOMICS_PARENT_TASK_B_V2.json"
ASTRA="brain_snapshot/canonical/runtime/astra_runtime.py"
PLAN=ROOT/"guarded_genomics_parent_b_public_runner_plan.json"

EXPECTED={
 TASK:"5f1a8fea0d29c2a60dcc7a038ecd557829e602e7",
 MISSION:"03e718a9c779c26d26e7af140f2f65549c1a7f6e",
 AUTH:"2cefd24591faf06ae307d7a4ece412e7b7836a6b",
 ASTRA:"426ffe58e405dc4f1ba2eb4e838e03a1df771964",
 "brain_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py":"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
 "brain_snapshot/canonical/runtime/bound_capabilities/open_research_source_frontend.py":"1ec11496aa84f261fc2c7e8e689ba687581d8b3c",
 "brain_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
 "brain_snapshot/canonical/runtime/bound_capabilities/objective_claim_operand_binding.py":"48fd058430d8d361fc75beced567c7b6d1166531",
 "brain_snapshot/canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py":"d66a7eb30774f66160b698d8082947776888293d",
 "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
 "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
 "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3",
}

def raw(path): return (ROOT/path).read_bytes()
def git_blob(path):
    b=raw(path)
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha256(path): return hashlib.sha256(raw(path)).hexdigest()

manifest=json.loads(MANIFEST.read_text())
if manifest.get("schema")!="PROJECT_BRAIN_EXACT_RUNTIME_SNAPSHOT_MANIFEST_V1": raise SystemExit("MANIFEST_SCHEMA")
if manifest.get("brain_commit")!="781d672f01533b71f6c46d729eec1d74aa6e20d8": raise SystemExit("MANIFEST_BRAIN_COMMIT")
files=manifest.get("files") or []
if manifest.get("runtime_file_count")!=96 or len(files)!=96: raise SystemExit("MANIFEST_RUNTIME_COUNT")
seen=set()
for item in files:
    path=item["path"]; want=item["git_blob_sha1"]
    if path in seen: raise SystemExit("MANIFEST_DUPLICATE:"+path)
    seen.add(path)
    got=git_blob(path)
    if got!=want: raise SystemExit("RUNTIME_BLOB_MISMATCH:"+path+":"+got+":"+want)
for path,want in EXPECTED.items():
    got=git_blob(path)
    if got!=want: raise SystemExit("EXACT_BLOB_MISMATCH:"+path+":"+got+":"+want)

task=json.loads((ROOT/TASK).read_text())
mission=json.loads((ROOT/MISSION).read_text())
auth=json.loads((ROOT/AUTH).read_text())
goal=task.get("goal_text")
if mission.get("goal")!=goal: raise SystemExit("MISSION_GOAL_MISMATCH")
if auth.get("task_id")!=task.get("task_id"): raise SystemExit("AUTH_TASK_MISMATCH")
if auth.get("task_blob_sha")!=EXPECTED[TASK]: raise SystemExit("AUTH_TASK_BLOB_MISMATCH")
if (mission.get("constraints") or {}).get("source_task_blob_sha")!=EXPECTED[TASK]: raise SystemExit("MISSION_TASK_BLOB_MISMATCH")
if (mission.get("constraints") or {}).get("no_same_task_replay") is not True: raise SystemExit("REPLAY_GUARD_MISSING")
if (mission.get("constraints") or {}).get("model_planner_disabled") is not True: raise SystemExit("MODEL_PLANNER_NOT_DISABLED")
if (task.get("execution_constraints") or {}).get("exactly_one_execution") is not True: raise SystemExit("EXACTLY_ONE_MISSING")
if task.get("freshness_class")!="FRESH_GENUINELY_OPEN_ENDED_PARENT_TASK_B": raise SystemExit("TASK_PHASE_NOT_B")

norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem=hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest()
pins=[{"path":x["path"],"git_blob_sha1":x["git_blob_sha1"]} for x in files]
for path,want in EXPECTED.items():
    if path not in seen:
        pins.append({"path":path,"git_blob_sha1":want})
pins.extend([
 {"path":"genomics_parent_b_runtime_manifest.json","git_blob_sha1":git_blob("genomics_parent_b_runtime_manifest.json")},
 {"path":"generate_guarded_genomics_parent_b_plan.py","git_blob_sha1":git_blob("generate_guarded_genomics_parent_b_plan.py")},
])

plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":goal,
 "frozen":{
   "gate_id":"BRAIN-GENOMICS-REFERENCE-LENGTH-PARENT-TASK-B-GUARDED-EXECUTION-20260930-V1",
   "problem_sha256":problem,
   "task_sha256":sha256(TASK),
   "runtime_sha256":sha256(ASTRA),
   "canonical_base":"781d672f01533b71f6c46d729eec1d74aa6e20d8",
   "authorization_sha256":sha256(AUTH),
 },
 "pinned_files":pins,
 "command":[
   "bash","-lc",
   "set -uo pipefail; mkdir -p _terminal; cd brain_snapshot; set +e; "
   "ASTRA_DISABLE_MODEL_PLANNER=1 python canonical/runtime/astra_runtime.py "
   "canonical/astra_runtime/missions/PARENT-OPENENDED-GENOMICS-REFERENCE-LENGTH-REAL-TASK-20260930-005.json "
   "2>&1 | tee ../_terminal/producer.log; code=${PIPESTATUS[0]}; "
   "printf '%s\\n' \"$code\" > ../_terminal/producer_exit_code.txt; "
   "if [ \"$code\" -ne 0 ]; then exit \"$code\"; fi; "
   "grep -Fq 'COMPOUND_GOAL_COMPLETE' ../_terminal/producer.log"
 ],
 "authority":{
   "brain_pr":497,
   "brain_authorization_merge":"781d672f01533b71f6c46d729eec1d74aa6e20d8",
   "task_id":task["task_id"],
   "parent_phase":"TASK_B",
   "no_same_task_replay":True,
   "model_dependency_count":0,
   "incremental_spend_usd":0,
   "snapshot_runtime_file_count":96,
 }
}
PLAN.write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({
 "status":"GENOMICS_PARENT_B_GUARDED_PLAN_READY",
 "problem_sha256":problem,
 "task_sha256":plan["frozen"]["task_sha256"],
 "runtime_sha256":plan["frozen"]["runtime_sha256"],
 "authorization_sha256":plan["frozen"]["authorization_sha256"],
 "pinned_file_count":len(pins),
},sort_keys=True))
