#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
TASK_REL="canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
RUNTIME_REL="canonical/runtime/astra_runtime.py"
REPORT=ROOT/"thermophysics-parent-terminal.json"
TASK_ID="PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
EXPECTED={
  RUNTIME_REL:"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
  "canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "canonical/runtime/auto_npm_library_acquisition.py":"b74cdf34a96fc2d591b902e1d582e0381a8a8d08",
  "canonical/runtime/auto_python_source_codec_acquisition.py":"65453b2eed5e678def3f0ab1c4d44182fb0b9a78",
  "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/verify_pending_cli_binding.py":"a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
  "canonical/runtime/promote_pending_binding.py":"f100c0d1ce5a4b07af0175035c3122d816459b0b",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
  TASK_REL:"dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
  MISSION_REL:"982b883b353b937d8500bd9b70c1929c33313393",
}

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True))

report={
  "schema":"PROJECT_BRAIN_FAITHFUL_OPEN_ENDED_PARENT_TERMINAL_V2",
  "task_id":TASK_ID,
  "brain_merge_commit":"fc07395c387563cbb2b3dfdc3b14fd80239a080b",
  "task_executed":False,
  "execution_count":0,
  "source_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "entrypoint":"canonical/runtime/astra_runtime.py <canonical mission path>",
  "direct_goal_compiler_harness_used":False,
  "replay_allowed":False,
}

# Exact-byte closure before spending the one-shot task.
for rel,expected in EXPECTED.items():
    path=ROOT/rel
    got=blob(path) if path.is_file() else None
    if got!=expected:
        report.update(status="PRESTART_CARRIER_CLOSURE_FAIL",path=rel,expected_blob=expected,observed_blob=got,replay_allowed=True)
        emit(report); raise SystemExit(1)

try:
    task=json.loads((ROOT/TASK_REL).read_text(encoding="utf-8"))
    mission=json.loads((ROOT/MISSION_REL).read_text(encoding="utf-8"))
except Exception as exc:
    report.update(status="PRESTART_CONTRACT_FAIL",first_causal_blocker=type(exc).__name__+":"+str(exc),replay_allowed=True)
    emit(report); raise SystemExit(1)

constraints=task.get("execution_constraints") or {}
anti=task.get("anti_leakage") or {}
mission_constraints=mission.get("constraints") or {}
if (
    os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1"
    or task.get("task_id")!=TASK_ID
    or task.get("source_task_replay") is not False
    or task.get("expected_answer_precommitted") is not False
    or constraints.get("exactly_one_execution") is not True
    or constraints.get("model_dependency_count")!=0
    or constraints.get("incremental_spend_usd")!=0
    or constraints.get("no_frontier_model_cognition") is not True
    or constraints.get("no_task_specific_runtime_patch") is not True
    or constraints.get("direct_goal_compiler_harness_forbidden") is not True
    or constraints.get("required_execution_entrypoint")!="canonical/runtime/astra_runtime.py <canonical mission path>"
    or any(anti.get(k) is not False for k in (
        "authority_name_preprovided","authority_domain_preprovided","source_url_preprovided",
        "dataset_identifier_preprovided","json_or_table_path_preprovided",
        "quantitative_formula_preprovided","controller_action_graph_preprovided",
        "expected_answer_precommitted"
    ))
    or mission.get("mission_id")!=TASK_ID
    or mission.get("goal")!=task.get("goal_text")
    or mission_constraints.get("model_dependency_count")!=0
    or mission_constraints.get("incremental_spend_usd")!=0
    or mission_constraints.get("model_planner_disabled") is not True
    or mission_constraints.get("fresh_parent_task") is not True
    or mission_constraints.get("exactly_one_execution") is not True
):
    report.update(status="PRESTART_POLICY_OR_CONTRACT_FAIL",first_causal_blocker="FROZEN_PARENT_CONTRACT_MISMATCH",replay_allowed=True)
    emit(report); raise SystemExit(1)

state_path=ROOT/"canonical/astra_runtime/state"/(TASK_ID+".json")
output_rel=task.get("required_output",{}).get("output_path")
output_path=ROOT/str(output_rel or "")
contaminated=[]
for p in (state_path,output_path):
    if p.is_file():
        contaminated.append(str(p.relative_to(ROOT)))
if contaminated:
    report.update(status="PRESTART_FRESHNESS_FAIL",first_causal_blocker="TASK_ID_OR_OUTPUT_ALREADY_HAS_RUNTIME_STATE",contaminated_paths=contaminated,replay_allowed=False)
    emit(report); raise SystemExit(1)

report["task_executed"]=True
report["execution_count"]=1
try:
    proc=subprocess.run(
      [sys.executable,str(ROOT/RUNTIME_REL),MISSION_REL],
      cwd=ROOT,text=True,capture_output=True,timeout=660,
      env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"}
    )
except subprocess.TimeoutExpired as exc:
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="CANONICAL_RUNTIME_TIMEOUT_660S",
      runtime_stdout_tail=(exc.stdout or "")[-12000:] if isinstance(exc.stdout,str) else "",
      runtime_stderr_tail=(exc.stderr or "")[-12000:] if isinstance(exc.stderr,str) else "",
      replay_allowed=False,
    )
    emit(report); raise SystemExit(2)

report["runtime_returncode"]=int(proc.returncode)
report["runtime_stdout_tail"]=(proc.stdout or "")[-12000:]
report["runtime_stderr_tail"]=(proc.stderr or "")[-12000:]

state=None
if state_path.is_file():
    try:
        state=json.loads(state_path.read_text(encoding="utf-8"))
        report["runtime_state"]=state
    except Exception as exc:
        report["runtime_state_parse_error"]=type(exc).__name__+":"+str(exc)
else:
    report["runtime_state_missing"]=True

producer=None
if output_rel and output_path.is_file():
    try:
        producer=json.loads(output_path.read_text(encoding="utf-8"))
        report["producer_output"]=producer
    except Exception as exc:
        report["producer_output_parse_error"]=type(exc).__name__+":"+str(exc)

if proc.returncode!=0 or not isinstance(state,dict) or state.get("status")!="COMPLETE":
    blocker=None
    if isinstance(state,dict):
        blocker=state.get("blocker") or state.get("error")
        if blocker is None and isinstance(state.get("last_blocker"),dict):
            blocker=state["last_blocker"].get("error") or state["last_blocker"].get("blocker")
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker=blocker or ("RUNTIME_RETURN_CODE_"+str(proc.returncode)),
      replay_allowed=False,
    )
    emit(report); raise SystemExit(2)

if not isinstance(producer,dict):
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="REQUIRED_DECISION_QUALITY_OUTPUT_MISSING_OR_INVALID",
      replay_allowed=False,
    )
    emit(report); raise SystemExit(3)

required=list(task.get("required_output",{}).get("fields") or [])
missing=[x for x in required if x not in producer]
if missing:
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="REQUIRED_OUTPUT_FIELDS_MISSING:"+",".join(missing),
      replay_allowed=False,
    )
    emit(report); raise SystemExit(4)

if producer.get("model_dependency_count")!=0:
    report.update(
      status="FAIL_FIRST_CAUSAL_GAP",
      parent_task_completed=False,
      independent_oracle_executed=False,
      first_causal_blocker="MODEL_INDEPENDENCE_CONTRACT_FAILED",
      replay_allowed=False,
    )
    emit(report); raise SystemExit(5)

report.update(
  status="PRODUCER_COMPLETED_PENDING_INDEPENDENT_ORACLE",
  parent_task_completed=False,
  producer_semantic_output_present=True,
  independent_oracle_executed=False,
  replay_allowed=False,
  parent_capability_credit_authorized=False,
  next_required_action="INDEPENDENTLY_REFETCH_PRODUCER_CITED_AUTHORITATIVE_SOURCES_AND_RECOMPUTE_DECLARED_METHOD_WITHOUT_IMPORTING_PRODUCER_MODULES",
)
emit(report)
