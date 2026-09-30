#!/usr/bin/env python3
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL = "canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
RESULT_REL = "canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
MISSION_ID = "PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
REPORT_REL = "fc073-thermophysics-openended-taska-terminal.json"
BRAIN_MAIN = "fc07395c387563cbb2b3dfdc3b14fd80239a080b"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    MISSION_REL: "982b883b353b937d8500bd9b70c1929c33313393",
    TASK_REL: "dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    (ROOT / REPORT_REL).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def find_key_values(value, key):
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                out.append(v)
            out.extend(find_key_values(v, key))
    elif isinstance(value, list):
        for v in value:
            out.extend(find_key_values(v, key))
    return out

def extract_urls(value):
    urls = []
    if isinstance(value, dict):
        for v in value.values():
            urls.extend(extract_urls(v))
    elif isinstance(value, list):
        for v in value:
            urls.extend(extract_urls(v))
    elif isinstance(value, str):
        urls.extend(re.findall(r"https?://[^\s\]\[\)\(\}\{<>\"']+", value))
    dedup = []
    for u in urls:
        u = u.rstrip(".,;:")
        if u not in dedup:
            dedup.append(u)
    return dedup

def numeric(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for k in ("value", "magnitude", "numeric_value", "amount"):
            if k in value:
                n = numeric(value[k])
                if n is not None:
                    return n
    if isinstance(value, str):
        m = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return None
    return None

def fetch(url, timeout=25, max_bytes=4000000):
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-Independent-Thermophysics-Oracle/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        final_url = resp.geturl()
        status = int(getattr(resp, "status", 200))
        ctype = str(resp.headers.get("Content-Type") or "")
    return {
        "requested_url": url,
        "final_url": final_url,
        "status": status,
        "content_type": ctype,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "body": raw.decode("utf-8", "replace"),
    }

report = {
    "schema": "PROJECT_BRAIN_FC073_THERMOPHYSICS_PARENT_TASK_A_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "mission_id": MISSION_ID,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
    "same_task_replay_forbidden_after_execution": True,
}

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        report.update({
            "status": "PRESTART_CARRIER_CLOSURE_FAIL",
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
            "replay_allowed": True,
            "replay_reason": "NO_PARENT_EXECUTION_OCCURRED",
        })
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "PRESTART_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
        "replay_allowed": True,
        "replay_reason": "NO_PARENT_EXECUTION_OCCURRED",
    })
    emit(report)
    raise SystemExit(1)

mission = safe_json(ROOT / MISSION_REL)
task = safe_json(ROOT / TASK_REL)
if not isinstance(mission, dict) or mission.get("mission_id") != MISSION_ID:
    report.update({"status": "PRESTART_POLICY_FAIL", "first_causal_blocker": "MISSION_ID_OR_JSON_INVALID", "replay_allowed": True})
    emit(report)
    raise SystemExit(1)
if not isinstance(task, dict) or task.get("task_id") != MISSION_ID:
    report.update({"status": "PRESTART_POLICY_FAIL", "first_causal_blocker": "TASK_ID_OR_JSON_INVALID", "replay_allowed": True})
    emit(report)
    raise SystemExit(1)

mc = mission.get("constraints") or {}
tc = task.get("execution_constraints") or {}
anti = task.get("anti_leakage") or {}
if (
    mc.get("model_dependency_count") != 0
    or mc.get("incremental_spend_usd") != 0
    or mc.get("model_planner_disabled") is not True
    or mc.get("fresh_parent_task") is not True
    or mc.get("exactly_one_execution") is not True
    or tc.get("model_dependency_count") != 0
    or tc.get("incremental_spend_usd") != 0
    or tc.get("no_frontier_model_cognition") is not True
    or tc.get("no_local_model") is not True
    or tc.get("no_model_artifact") is not True
    or tc.get("no_task_specific_runtime_patch") is not True
    or tc.get("exactly_one_execution") is not True
    or tc.get("stop_on_first_causal_gap") is not True
    or tc.get("direct_goal_compiler_harness_forbidden") is not True
    or tc.get("required_execution_entrypoint") != "canonical/runtime/astra_runtime.py <canonical mission path>"
    or any(anti.get(k) is not False for k in (
        "authority_name_preprovided", "authority_domain_preprovided", "source_url_preprovided",
        "dataset_identifier_preprovided", "json_or_table_path_preprovided", "quantitative_formula_preprovided",
        "controller_action_graph_preprovided", "expected_answer_precommitted"
    ))
):
    report.update({
        "status": "PRESTART_POLICY_FAIL",
        "first_causal_blocker": "FROZEN_TASK_OR_MISSION_CONTRACT_INVALID",
        "replay_allowed": True,
        "replay_reason": "NO_PARENT_EXECUTION_OCCURRED",
    })
    emit(report)
    raise SystemExit(1)

state_path = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
result_path = ROOT / RESULT_REL
if state_path.exists() or result_path.exists():
    report.update({
        "status": "PRESTART_FRESHNESS_FAIL",
        "first_causal_blocker": "TASK_STATE_OR_RESULT_ALREADY_PRESENT",
        "state_exists": state_path.exists(),
        "result_exists": result_path.exists(),
        "replay_allowed": False,
    })
    emit(report)
    raise SystemExit(1)

report["execution_count"] = 1
report["task_executed"] = True
proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=720,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["producer_returncode"] = int(proc.returncode)
report["producer_stdout_tail"] = proc.stdout[-16000:]
report["producer_stderr_tail"] = proc.stderr[-16000:]
state = safe_json(state_path) if state_path.is_file() else None
result = safe_json(result_path) if result_path.is_file() else None
report["producer_state"] = state
report["producer_result"] = result

if proc.returncode != 0:
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "independent_oracle_executed": False,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "CANONICAL_RUNTIME",
        "first_causal_blocker": (
            (state or {}).get("blocker")
            or (state or {}).get("error")
            or proc.stderr[-4000:]
            or proc.stdout[-4000:]
            or "CANONICAL_RUNTIME_NONZERO"
        ),
    })
    emit(report)
    raise SystemExit(2)

if not isinstance(state, dict) or state.get("status") != "COMPLETE":
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "independent_oracle_executed": False,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "CANONICAL_RUNTIME_STATE",
        "first_causal_blocker": "RUNTIME_RETURNED_ZERO_WITHOUT_COMPLETE_STATE",
    })
    emit(report)
    raise SystemExit(3)

if not isinstance(result, dict):
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "independent_oracle_executed": False,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "RESULT_MATERIALIZATION",
        "first_causal_blocker": "REQUIRED_RESULT_JSON_NOT_MATERIALIZED",
    })
    emit(report)
    raise SystemExit(4)

model_counts = []
for raw in find_key_values({"state": state, "result": result}, "model_dependency_count"):
    try:
        model_counts.append(int(raw))
    except Exception:
        model_counts.append(-1)
report["observed_model_dependency_counts"] = model_counts
if any(v != 0 for v in model_counts):
    report.update({
        "status": "FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed": False,
        "independent_oracle_executed": False,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "COGNITION_PROVENANCE",
        "first_causal_blocker": "NONZERO_OR_INVALID_MODEL_DEPENDENCY_COUNT",
    })
    emit(report)
    raise SystemExit(5)

required_fields = list((task.get("required_output") or {}).get("fields") or [])
missing = [k for k in required_fields if k not in result]
if missing:
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "ORACLE_OUTPUT_CONTRACT",
        "first_causal_blocker": "MISSING_REQUIRED_RESULT_FIELDS",
        "missing_fields": missing,
    })
    emit(report)
    raise SystemExit(6)

v20 = numeric(result.get("viscosity_20c"))
v40 = numeric(result.get("viscosity_40c"))
declared_ratio = numeric(result.get("ratio_40c_to_20c"))
if v20 is None or v40 is None or v20 <= 0 or v40 <= 0:
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "ORACLE_NUMERIC_PARSE",
        "first_causal_blocker": "VISCOSITY_FIELDS_NOT_POSITIVE_NUMERIC",
    })
    emit(report)
    raise SystemExit(7)

oracle_ratio = v40 / v20
ratio_ok = declared_ratio is not None and math.isclose(declared_ratio, oracle_ratio, rel_tol=2e-3, abs_tol=2e-6)
oracle_decision = oracle_ratio < 0.5
decision_text = str(result.get("decision") or "").strip().lower()
if oracle_decision:
    decision_ok = any(tok in decision_text for tok in ("yes", "true", "less than half", "below half", "< 0.5", "<0.5"))
else:
    decision_ok = any(tok in decision_text for tok in ("no", "false", "not less", "greater than", "above half", ">= 0.5", ">=0.5"))

urls = extract_urls(result.get("source_provenance"))
fetches = []
for url in urls[:6]:
    try:
        f = fetch(url)
        body_lower = f.pop("body").lower()
        f["mentions_water"] = "water" in body_lower
        f["mentions_viscosity"] = "viscos" in body_lower
        f["mentions_20"] = "20" in body_lower
        f["mentions_40"] = "40" in body_lower
        f["semantic_reference_match"] = f["mentions_water"] and f["mentions_viscosity"] and (f["mentions_20"] or f["mentions_40"])
        fetches.append(f)
    except Exception as exc:
        fetches.append({"requested_url": url, "error": type(exc).__name__ + ":" + str(exc), "semantic_reference_match": False})

source_refetch_ok = bool(fetches) and any(x.get("semantic_reference_match") for x in fetches)
report["independent_oracle"] = {
    "producer_modules_imported": False,
    "source_task_replayed": False,
    "producer_cited_urls": urls,
    "refetches": fetches,
    "parsed_viscosity_20c": v20,
    "parsed_viscosity_40c": v40,
    "recomputed_ratio_40c_to_20c": oracle_ratio,
    "declared_ratio": declared_ratio,
    "ratio_matches": ratio_ok,
    "recomputed_decision_less_than_half": oracle_decision,
    "producer_decision": result.get("decision"),
    "decision_matches": decision_ok,
    "source_refetch_semantic_check": source_refetch_ok,
}

if not (ratio_ok and decision_ok and source_refetch_ok):
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "independent_oracle_verified": False,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "INDEPENDENT_ORACLE",
        "first_causal_blocker": "SOURCE_REFETCH_OR_RECOMPUTATION_DID_NOT_VERIFY",
    })
    emit(report)
    raise SystemExit(8)

report.update({
    "status": "PASS_PRODUCER_AND_INDEPENDENT_ORACLE",
    "parent_task_completed": True,
    "independent_oracle_executed": True,
    "independent_oracle_verified": True,
    "model_dependency_count": 0,
    "incremental_spend_usd": 0,
    "replay_allowed": False,
    "parent_capability_credit_authorized": False,
    "next_required_action": "RECONCILE_EXACT_RECEIPT_IN_CANONICAL_BRAIN_BEFORE_ANY_CAPABILITY_CREDIT_OR_PROMOTION",
})
emit(report)
