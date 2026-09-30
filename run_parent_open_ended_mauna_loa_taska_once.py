#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = ROOT / "canonical" / "runtime"
TASK_PATH = ROOT / "canonical" / "tasks" / "PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT = ROOT / "parent-open-ended-mauna-loa-taska-terminal.json"
CLOSURE_MANIFEST = ROOT / "PARENT_RUNTIME_ADAPTER_CLOSURE_MANIFEST_V1.json"

TASK_ID = "PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"
EXPECTED_BRAIN_RUNTIME_BASE = "797d5fbea5f230a31044006755beb98ae387134b"
EXPECTED_RUNTIME_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))

def fail_prestart(reason, **extra):
    report = {
        "schema": "PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_TERMINAL_V1",
        "status": "CARRIER_PRESTART_FAIL",
        "task_id": TASK_ID,
        "task_executed": False,
        "execution_count": 0,
        "same_task_replay_allowed": True,
        "reason": reason,
        **extra,
    }
    emit(report)
    raise SystemExit(10)

if not TASK_PATH.is_file():
    fail_prestart("FROZEN_TASK_MISSING")
if not CLOSURE_MANIFEST.is_file():
    fail_prestart("PARENT_RUNTIME_CLOSURE_MANIFEST_MISSING")

try:
    closure = json.loads(CLOSURE_MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    fail_prestart("PARENT_RUNTIME_CLOSURE_MANIFEST_INVALID", error=type(exc).__name__ + ":" + str(exc))

if closure.get("brain_base_commit") != EXPECTED_BRAIN_RUNTIME_BASE:
    fail_prestart(
        "PARENT_RUNTIME_BASE_MISMATCH",
        expected=EXPECTED_BRAIN_RUNTIME_BASE,
        observed=closure.get("brain_base_commit"),
    )

for rel, expected in EXPECTED_RUNTIME_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        fail_prestart("RUNTIME_BLOB_MISMATCH", path=rel, expected=expected, observed=observed)

try:
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    fail_prestart("FROZEN_TASK_INVALID_JSON", error=type(exc).__name__ + ":" + str(exc))

if task.get("task_id") != TASK_ID:
    fail_prestart("TASK_ID_MISMATCH", observed=task.get("task_id"))
if task.get("source_task_replay") is not False:
    fail_prestart("TASK_REPLAY_FLAG_INVALID")
anti = task.get("anti_leakage") or {}
required_anti = {
    "authority_name_preprovided",
    "authority_domain_preprovided",
    "source_url_preprovided",
    "dataset_identifier_preprovided",
    "json_or_table_path_preprovided",
    "quantitative_formula_preprovided",
    "controller_action_graph_preprovided",
    "expected_answer_precommitted",
}
if set(anti) != required_anti or any(anti.get(k) is not False for k in required_anti):
    fail_prestart("ANTI_LEAKAGE_CONTRACT_INVALID", anti_leakage=anti)
constraints = task.get("execution_constraints") or {}
for key in ("no_frontier_model_cognition", "no_local_model", "no_model_artifact", "no_task_specific_runtime_patch", "exactly_one_execution", "stop_on_first_causal_gap"):
    if constraints.get(key) is not True:
        fail_prestart("TASK_EXECUTION_CONTRACT_INVALID", key=key, observed=constraints.get(key))
if constraints.get("model_dependency_count") != 0 or constraints.get("incremental_spend_usd") != 0:
    fail_prestart("TASK_DEPENDENCY_OR_SPEND_CONTRACT_INVALID")

goal = str(task.get("goal_text") or "").strip()
if not goal:
    fail_prestart("TASK_GOAL_MISSING")
if "http://" in goal.lower() or "https://" in goal.lower():
    fail_prestart("SOURCE_URL_LEAKED_INTO_GOAL")

output_rel = str((task.get("required_output") or {}).get("output_path") or "").strip()
required_fields = list((task.get("required_output") or {}).get("fields") or [])
if not output_rel or not required_fields:
    fail_prestart("REQUIRED_OUTPUT_CONTRACT_MISSING")
output_path = ROOT / output_rel
if output_path.exists():
    fail_prestart("STALE_REQUIRED_OUTPUT_PRESENT_BEFORE_EXECUTION", output_path=output_rel)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

try:
    runtime = load_module("parent_open_ended_taska_astra_runtime", RUNTIME / "astra_runtime.py")
except Exception as exc:
    fail_prestart(
        "RUNTIME_IMPORT_CLOSURE_FAIL",
        error=type(exc).__name__ + ":" + str(exc),
        traceback=traceback.format_exc()[-5000:],
    )

os.environ["ASTRA_DISABLE_MODEL_PLANNER"] = "1"

report = {
    "schema": "PROJECT_BRAIN_PARENT_OPEN_ENDED_TASK_A_TERMINAL_V1",
    "status": "STARTED",
    "task_id": TASK_ID,
    "brain_runtime_base": EXPECTED_BRAIN_RUNTIME_BASE,
    "task_executed": True,
    "execution_count": 1,
    "same_task_replay_allowed": False,
    "incremental_spend_usd": 0,
    "producer_goal": goal,
    "predeclared_source_url": False,
    "predeclared_authority_domain": False,
    "predeclared_formula": False,
    "predeclared_controller_actions": False,
}
emit(report)

mission = {"mission_id": TASK_ID, "goal": goal}
step = {
    "id": "parent-open-ended-task-a",
    "adapter": "goal",
    "goal_ref": "goal",
    "allow_optional_model_planner": False,
}

try:
    result = runtime.run_goal(step, mission)
except Exception as exc:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "RUN_GOAL:" + type(exc).__name__ + ":" + str(exc),
        "producer_traceback": traceback.format_exc()[-10000:],
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(20)

report["runtime_result"] = result
report["runtime_cognition_provenance"] = {
    "cognition_provenance_authority": result.get("cognition_provenance_authority") if isinstance(result, dict) else None,
    "cognition_dependency_class": result.get("cognition_dependency_class") if isinstance(result, dict) else None,
    "model_dependency_count": result.get("model_dependency_count") if isinstance(result, dict) else None,
    "controller_mode": result.get("controller_mode") if isinstance(result, dict) else None,
    "planner_source": result.get("planner_source") if isinstance(result, dict) else None,
    "planner_transport": result.get("planner_transport") if isinstance(result, dict) else None,
    "planner_model_last": result.get("planner_model_last") if isinstance(result, dict) else None,
}

if not isinstance(result, dict):
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "PUBLIC_RUN_GOAL_RESULT_NOT_OBJECT",
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(21)

if result.get("cognition_provenance_authority") != "ASTRA_RUNTIME_DERIVED_V1":
    report.update({
        "status": "FAIL_COGNITION_PROVENANCE",
        "parent_task_completed": False,
        "first_causal_blocker": "RUNTIME_DERIVED_COGNITION_PROVENANCE_MISSING",
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(22)

if result.get("model_dependency_count") != 0 or result.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
    report.update({
        "status": "FAIL_MODEL_DEPENDENCY",
        "parent_task_completed": False,
        "first_causal_blocker": "PRODUCER_NOT_MODEL_INDEPENDENT",
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(23)

trace = result.get("trace") or []
action_types = []
for item in trace if isinstance(trace, list) else []:
    if isinstance(item, dict):
        plan = item.get("plan") or {}
        if isinstance(plan, dict) and plan.get("type"):
            action_types.append(str(plan.get("type")))
report["observed_action_types"] = action_types

discovery_actions = {"resolve_authority_identity", "discover_authoritative_web_source", "discover_authoritative_source"}
if not any(x in discovery_actions for x in action_types):
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "OPEN_ENDED_MATERIAL_SOURCE_OR_TOOL_DISCOVERY_NOT_OBSERVED",
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(24)

if not output_path.is_file():
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "OPEN_ENDED_REQUIRED_DECISION_RESULT_NOT_MATERIALIZED",
        "required_output_path": output_rel,
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(25)

try:
    producer = json.loads(output_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "OPEN_ENDED_REQUIRED_DECISION_RESULT_INVALID_JSON",
        "error": type(exc).__name__ + ":" + str(exc),
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(26)

missing = [k for k in required_fields if k not in producer]
if missing:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_blocker": "OPEN_ENDED_REQUIRED_DECISION_FIELDS_MISSING",
        "missing_required_fields": missing,
        "producer_result": producer,
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(27)

if producer.get("model_dependency_count") != 0:
    report.update({
        "status": "FAIL_MODEL_DEPENDENCY",
        "parent_task_completed": False,
        "first_causal_blocker": "MATERIALIZED_RESULT_MODEL_DEPENDENCY_NONZERO_OR_MISSING",
        "producer_result": producer,
        "independent_oracle_executed": False,
    })
    emit(report)
    raise SystemExit(28)

report.update({
    "status": "PRODUCER_COMPLETED_PENDING_INDEPENDENT_ORACLE",
    "parent_task_completed": False,
    "producer_semantic_result_materialized": True,
    "producer_result": producer,
    "independent_oracle_executed": False,
    "next_action": "INDEPENDENTLY_VERIFY_PRODUCER_CITED_PRIMARY_EVIDENCE_AND_RECOMPUTE_DECLARED_METHOD_WITHOUT_REPLAY",
})
emit(report)
