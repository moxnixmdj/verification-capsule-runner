#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
MISSION_REL="canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL="canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_ID="PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
REPORT=ROOT/"thermophysics-parent-a-terminal.json"
STATE=ROOT/"canonical/astra_runtime/state"/(MISSION_ID+".json")
EVID=ROOT/"canonical/astra_runtime/evidence"
OUTPUT=ROOT/"canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
EXPECTED={
 "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
 "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
 "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
 "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
 "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
 "canonical/runtime/semantic_authorities.py":"1d74b9c2cdc0e387ab1d64f04c8f38f414f2d80e",
 "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
 "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
 "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
 "canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json":"982b883b353b937d8500bd9b70c1929c33313393",
 "canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json":"dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
}
def blob(path):
 raw=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def readj(p):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None
def emit(x):
 REPORT.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(x,indent=2,sort_keys=True))
report={"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_A_TERMINAL_V1","brain_main":"fc07395c387563cbb2b3dfdc3b14fd80239a080b","mission_id":MISSION_ID,"execution_count":0,"task_executed":False,"model_dependency_count":0,"incremental_spend_usd":0}
for rel,exp in EXPECTED.items():
 p=ROOT/rel; obs=blob(p) if p.is_file() else None
 if obs!=exp:
  report.update(status="PRESTART_CARRIER_CLOSURE_FAIL",path=rel,expected_blob=exp,observed_blob=obs)
  emit(report); raise SystemExit(10)
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
 report.update(status="PRESTART_POLICY_FAIL",first_causal_blocker="MODEL_PLANNER_NOT_DISABLED");emit(report);raise SystemExit(11)
task=readj(ROOT/TASK_REL); mission=readj(ROOT/MISSION_REL)
if not isinstance(task,dict) or task.get("task_id")!=MISSION_ID or not isinstance(mission,dict) or mission.get("mission_id")!=MISSION_ID:
 report.update(status="PRESTART_POLICY_FAIL",first_causal_blocker="FROZEN_TASK_OR_MISSION_IDENTITY_INVALID");emit(report);raise SystemExit(12)
c=task.get("execution_constraints") or {}
if c.get("exactly_one_execution") is not True or c.get("model_dependency_count")!=0 or c.get("incremental_spend_usd")!=0 or c.get("direct_goal_compiler_harness_forbidden") is not True:
 report.update(status="PRESTART_POLICY_FAIL",first_causal_blocker="FROZEN_EXECUTION_CONTRACT_INVALID");emit(report);raise SystemExit(13)
contam=[]
if STATE.exists():contam.append(str(STATE.relative_to(ROOT)))
for p in EVID.glob(MISSION_ID+"*"):
 contam.append(str(p.relative_to(ROOT)))
if OUTPUT.exists():contam.append(str(OUTPUT.relative_to(ROOT)))
if contam:
 report.update(status="PRESTART_FRESHNESS_FAIL",first_causal_blocker="MISSION_ALREADY_HAS_RUNTIME_EVIDENCE",contaminated_paths=sorted(contam))
 emit(report);raise SystemExit(14)
report["execution_count"]=1;report["task_executed"]=True
proc=subprocess.run([sys.executable,"canonical/runtime/astra_runtime.py",MISSION_REL],cwd=ROOT,text=True,capture_output=True,timeout=660,env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"})
state=readj(STATE)
blocker=(state or {}).get("blocker") if isinstance(state,dict) else None
producer=readj(OUTPUT) if OUTPUT.exists() else None
report.update(runtime_returncode=proc.returncode,runtime_stdout_tail=(proc.stdout or "")[-12000:],runtime_stderr_tail=(proc.stderr or "")[-12000:],runtime_state=state,producer_output=producer,replay_allowed=False)
if proc.returncode!=0:
 report.update(status="FAIL_FIRST_CAUSAL_GAP",parent_task_completed=False,first_causal_blocker=(blocker or {}).get("error") if isinstance(blocker,dict) else "RUNTIME_NONZERO_WITHOUT_STRUCTURED_BLOCKER",independent_oracle_executed=False)
 emit(report);raise SystemExit(2)
if not isinstance(producer,dict):
 report.update(status="FAIL_FIRST_CAUSAL_GAP",parent_task_completed=False,first_causal_blocker="REQUIRED_DECISION_QUALITY_OUTPUT_MISSING",independent_oracle_executed=False)
 emit(report);raise SystemExit(3)
required=(task.get("required_output") or {}).get("fields") or []
missing=[x for x in required if x not in producer]
if missing:
 report.update(status="FAIL_FIRST_CAUSAL_GAP",parent_task_completed=False,first_causal_blocker="REQUIRED_OUTPUT_FIELDS_MISSING:"+",".join(missing),independent_oracle_executed=False)
 emit(report);raise SystemExit(4)
md=producer.get("model_dependency_count")
if md!=0:
 report.update(status="FAIL_FIRST_CAUSAL_GAP",parent_task_completed=False,first_causal_blocker="MODEL_DEPENDENCY_COUNT_NONZERO",model_dependency_count=md,independent_oracle_executed=False)
 emit(report);raise SystemExit(5)
report.update(status="PRODUCER_COMPLETED_PENDING_INDEPENDENT_ORACLE",parent_task_completed=False,model_dependency_count=0,independent_oracle_executed=False,next_required_action="RUN_INDEPENDENT_SOURCE_AND_CALCULATION_ORACLE_WITHOUT_REPLAYING_PRODUCER")
emit(report)
