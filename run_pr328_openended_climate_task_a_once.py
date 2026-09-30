#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = ROOT / "canonical" / "runtime"
TASK_PATH = ROOT / "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json"
REPORT = ROOT / "pr328-openended-climate-task-a-terminal.json"

BRAIN_BASE = "aa8f55bd9ead298ec0380bd9dbf45bc8d7c41a8e"
BRAIN_PR = 328
BRAIN_HEAD = "ccc9209c4d29bc7a04fc4ff2aaf5c459e91ea832"
TASK_ID = "PARENT-CLIMATE-MAUNA-LOA-CO2-ACCELERATION-OPEN-RESEARCH-TASK-A-20260930-001"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "a73410e38d4c67d92188e934e0c0c3f0b2b329ee",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/capability_planner.py": "64ff65cb184f50d3336326f33cccfcc0a53301a8",
    "canonical/runtime/capability_proposal_generators.py": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py": "6385b469f1287c971217dcac58af2ffebd81f9fd",
    "canonical/runtime/bound_capabilities/grounded_executable_composition.py": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
    "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
    "canonical/tasks/PARENT_CLIMATE_MAUNA_LOA_CO2_ACCELERATION_OPEN_RESEARCH_TASK_A_20260930_001.json": "6f0e889e23cfba6c511b3a54cb86acba48bc9d3a",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        emit({
            "schema": "PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
            "status": "CARRIER_CLOSURE_FAIL",
            "brain_pr": BRAIN_PR,
            "brain_base": BRAIN_BASE,
            "brain_head": BRAIN_HEAD,
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
            "task_executed": False,
            "execution_count": 0,
        })
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    emit({
        "schema": "PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
        "task_executed": False,
        "execution_count": 0,
    })
    raise SystemExit(1)

task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
if task.get("task_id") != TASK_ID:
    raise SystemExit("TASK_ID_MISMATCH")
constraints = task.get("execution_constraints") or {}
anti = task.get("anti_leakage") or {}
if (
    constraints.get("exactly_one_execution") is not True
    or constraints.get("model_dependency_count") != 0
    or constraints.get("incremental_spend_usd") != 0
    or constraints.get("no_frontier_model_cognition") is not True
    or constraints.get("no_local_model") is not True
    or constraints.get("no_model_artifact") is not True
    or constraints.get("stop_on_first_causal_gap") is not True
):
    raise SystemExit("TASK_EXECUTION_CONTRACT_INVALID")
if any(anti.get(k) is not False for k in (
    "authority_name_preprovided",
    "authority_domain_preprovided",
    "source_url_preprovided",
    "dataset_identifier_preprovided",
    "json_or_table_path_preprovided",
    "quantitative_formula_preprovided",
    "controller_action_graph_preprovided",
    "expected_answer_precommitted",
)):
    raise SystemExit("TASK_ANTI_LEAKAGE_CONTRACT_INVALID")

compiler = load("pr328_goal_compiler", RUNTIME / "goal_compiler.py")
runtime = load("pr328_astra_runtime", RUNTIME / "astra_runtime.py")
registry = json.loads((RUNTIME / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]

report = {
    "schema": "PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V1",
    "status": "STARTED",
    "brain_pr": BRAIN_PR,
    "brain_base": BRAIN_BASE,
    "brain_head": BRAIN_HEAD,
    "task_id": TASK_ID,
    "task_blob": EXPECTED_BLOBS[str(TASK_PATH.relative_to(ROOT))],
    "domain": task.get("domain"),
    "source_task_replay": False,
    "execution_count": 1,
    "model_dependency_count": 0,
    "incremental_spend_usd": 0,
    "model_planner_disabled": True,
    "anti_leakage": anti,
}

goal = str(task["goal_text"])
try:
    compiled = compiler.compile_goal(goal, registry, ROOT)
except Exception as exc:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "task_executed": True,
        "parent_task_completed": False,
        "first_causal_stage": "COMPILE",
        "first_causal_blocker": "COMPILE:" + type(exc).__name__ + ":" + str(exc),
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(2)

report["compiled_route"] = {
    "compiler_mode": compiled.get("compiler_mode"),
    "clause_coverage_verified": compiled.get("clause_coverage_verified"),
    "clause_count": len(compiled.get("clauses") or []),
    "compiled_part_count": len(compiled.get("compiled_parts") or []),
    "controller_action_count": len(compiled.get("controller_actions") or []),
}

mission = {"mission_id": TASK_ID, "goal": goal}
step = {
    "id": "parent_openended_climate_task_a",
    "controller_actions": compiled["controller_actions"],
    "max_controller_actions": 64,
}
try:
    run = runtime._run_model_independent_goal(step, mission, goal)
    run = runtime._stamp_cognition_provenance(run)
except Exception as exc:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "task_executed": True,
        "parent_task_completed": False,
        "first_causal_stage": "EXECUTE",
        "first_causal_blocker": "EXECUTE:" + type(exc).__name__ + ":" + str(exc),
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(3)

report["runtime_result"] = run
report["model_dependency_count"] = run.get("model_dependency_count")
report["cognition_dependency_class"] = run.get("cognition_dependency_class")
if run.get("model_dependency_count") != 0 or run.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_stage": "COGNITION_PROVENANCE",
        "first_causal_blocker": "MODEL_INDEPENDENCE_CONTRACT_FAILED",
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(4)

output_path = ROOT / str((task.get("required_output") or {}).get("output_path") or "")
if not output_path.is_file():
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_stage": "OUTPUT",
        "first_causal_blocker": "REQUIRED_DECISION_QUALITY_OUTPUT_MISSING",
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(5)

try:
    producer = json.loads(output_path.read_text(encoding="utf-8"))
except Exception as exc:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_stage": "OUTPUT",
        "first_causal_blocker": "REQUIRED_OUTPUT_JSON_INVALID:" + type(exc).__name__,
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(6)

required_fields = list((task.get("required_output") or {}).get("fields") or [])
missing = [field for field in required_fields if field not in producer]
if missing:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "first_causal_stage": "OUTPUT",
        "first_causal_blocker": "REQUIRED_OUTPUT_FIELDS_MISSING:" + ",".join(missing),
        "producer_output": producer,
        "independent_oracle_executed": False,
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(7)

report.update({
    "status": "PRODUCER_COMPLETED_PENDING_INDEPENDENT_VERIFICATION",
    "parent_task_completed": False,
    "producer_semantic_output_present": True,
    "producer_output": producer,
    "independent_oracle_executed": False,
    "parent_capability_credit_authorized": False,
    "replay_allowed": False,
    "next_required_action": "INDEPENDENTLY_REFETCH_PRODUCER_CITED_PRIMARY_SOURCES_AND_RECOMPUTE_DECLARED_METHOD_WITHOUT_IMPORTING_PRODUCER_MODULES",
})
emit(report)
