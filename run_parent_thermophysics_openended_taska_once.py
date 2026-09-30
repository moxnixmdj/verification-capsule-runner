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
BRAIN_AUTHORITY = "fc07395c387563cbb2b3dfdc3b14fd80239a080b"
RUNNER_BASE = "eff796468741f509650904cd7fbaf8eab3958ff1"
MISSION_ID = "PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
MISSION_REL = "canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL = "canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
INTENT_REL = "canonical/action_intents/2026-09-30_PARENT_THERMOPHYSICS_FAITHFUL_RUNTIME_TASK_A_002.json"
RESULT_REL = "canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
REPORT_PATH = ROOT / "parent-thermophysics-openended-taska-terminal.json"
ARM_PATH = ROOT / "ARM_PARENT_THERMOPHYSICS_TASK_A_20260930_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/python_codec_probe.py": "fc8b5005a9888422e3cb61f6cf0bd147c740ec84",
    "canonical/runtime/verify_pending_cli_binding.py": "a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
    "canonical/runtime/promote_pending_binding.py": "f100c0d1ce5a4b07af0175035c3122d816459b0b",
    MISSION_REL: "982b883b353b937d8500bd9b70c1929c33313393",
    TASK_REL: "dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
    INTENT_REL: "9d86ae7e9678d9a860039b865a3af4052d1099f9",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def collect_named(value, key):
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                out.append(v)
            out.extend(collect_named(v, key))
    elif isinstance(value, list):
        for item in value:
            out.extend(collect_named(item, key))
    return out

def collect_urls(value):
    out = []
    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            for u in re.findall(r"https?://[^\s\"'<>\]\)]+", v):
                if u not in out:
                    out.append(u.rstrip(".,;"))
    walk(value)
    return out

def numeric_value(v):
    if isinstance(v, bool):
        raise ValueError("boolean is not numeric")
    if isinstance(v, (int, float)):
        x = float(v)
        if math.isfinite(x):
            return x
    if isinstance(v, dict):
        for k in ("value", "numeric_value", "amount", "mean"):
            if k in v:
                try:
                    return numeric_value(v[k])
                except Exception:
                    pass
    if isinstance(v, str):
        m = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", v.replace(",", ""))
        if m:
            x = float(m.group(0))
            if math.isfinite(x):
                return x
    raise ValueError("no finite numeric value")

def decision_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    negative = ("not less", "no", "false", "greater than or equal", "at least half")
    positive = ("yes", "true", "less than half", "below half", "< 0.5", "<0.5")
    if any(x in s for x in negative):
        return False
    if any(x in s for x in positive):
        return True
    raise ValueError("decision not machine-checkable")

def fetch_text(url, timeout=25, max_bytes=4_000_000):
    req = urllib.request.Request(url, headers={"User-Agent":"ProjectBrain-Thermophysics-Independent-Oracle/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        return {
            "requested_url": url,
            "final_url": resp.geturl(),
            "status": int(getattr(resp, "status", 200)),
            "content_type": str(resp.headers.get("Content-Type") or ""),
            "sha256": sha256_bytes(raw),
            "text": raw.decode("utf-8", "replace"),
        }

def numeric_tokens(x):
    vals = [x, x * 1000.0, x / 1000.0]
    out = set()
    for value in vals:
        for n in range(2, 8):
            out.add(f"{value:.{n}g}".lower())
            out.add(f"{value:.{n}f}".rstrip("0").rstrip(".").lower())
    return {t for t in out if t and t not in {"0", "-0"}}

report = {
    "schema": "PROJECT_BRAIN_PARENT_THERMOPHYSICS_TASK_A_TERMINAL_V1",
    "brain_authority": BRAIN_AUTHORITY,
    "runner_base": RUNNER_BASE,
    "mission_id": MISSION_ID,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
    "same_task_replay_forbidden_after_start": True,
}

if not ARM_PATH.is_file():
    report.update({"status":"PRESTART_NOT_ARMED","replay_allowed":True})
    emit(report)
    raise SystemExit(1)

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        report.update({
            "status":"PRESTART_CARRIER_CLOSURE_FAIL",
            "path":rel,
            "expected_blob":expected,
            "observed_blob":observed,
            "replay_allowed":True,
            "replay_reason":"NO_PRODUCER_ENTRY",
        })
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({"status":"PRESTART_POLICY_FAIL","first_causal_blocker":"MODEL_PLANNER_NOT_DISABLED","replay_allowed":True})
    emit(report)
    raise SystemExit(1)

mission = safe_json(ROOT / MISSION_REL)
task = safe_json(ROOT / TASK_REL)
intent = safe_json(ROOT / INTENT_REL)
if not all(isinstance(x, dict) for x in (mission, task, intent)):
    report.update({"status":"PRESTART_AUTHORITY_PARSE_FAIL","replay_allowed":True})
    emit(report)
    raise SystemExit(1)
if mission.get("mission_id") != MISSION_ID or task.get("task_id") != MISSION_ID:
    report.update({"status":"PRESTART_AUTHORITY_ID_FAIL","replay_allowed":True})
    emit(report)
    raise SystemExit(1)

mc = mission.get("constraints") or {}
tc = task.get("execution_constraints") or {}
anti = task.get("anti_leakage") or {}
if not (
    mc.get("model_dependency_count") == 0
    and mc.get("incremental_spend_usd") == 0
    and mc.get("model_planner_disabled") is True
    and mc.get("fresh_parent_task") is True
    and mc.get("exactly_one_execution") is True
    and tc.get("model_dependency_count") == 0
    and tc.get("incremental_spend_usd") == 0
    and tc.get("no_frontier_model_cognition") is True
    and tc.get("no_local_model") is True
    and tc.get("no_model_artifact") is True
    and tc.get("no_task_specific_runtime_patch") is True
    and tc.get("exactly_one_execution") is True
    and tc.get("stop_on_first_causal_gap") is True
    and tc.get("direct_goal_compiler_harness_forbidden") is True
    and tc.get("required_execution_entrypoint") == "canonical/runtime/astra_runtime.py <canonical mission path>"
    and anti
    and all(v is False for v in anti.values())
):
    report.update({"status":"PRESTART_AUTHORITY_CONTRACT_FAIL","replay_allowed":True})
    emit(report)
    raise SystemExit(1)

# Producer spend begins here. After this line the task is permanently spent.
report["execution_count"] = 1
report["task_executed"] = True
report["replay_allowed"] = False

proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=720,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER":"1"},
)
report["producer_returncode"] = int(proc.returncode)
report["producer_stdout_tail"] = proc.stdout[-16000:]
report["producer_stderr_tail"] = proc.stderr[-16000:]

state_path = ROOT / "canonical/astra_runtime/state" / f"{MISSION_ID}.json"
state = safe_json(state_path) if state_path.is_file() else None
report["producer_state"] = state
report["state_path"] = str(state_path.relative_to(ROOT))

evidence_dir = ROOT / "canonical/astra_runtime/evidence"
if evidence_dir.is_dir():
    report["producer_evidence_files"] = sorted(
        str(p.relative_to(ROOT)) for p in evidence_dir.glob(MISSION_ID + "*") if p.is_file()
    )

if proc.returncode != 0 or not isinstance(state, dict) or state.get("status") != "COMPLETE":
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed":False,
        "independent_oracle_executed":False,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"CANONICAL_RUNTIME",
        "first_causal_blocker": (
            (state or {}).get("blocker")
            or (state or {}).get("error")
            or proc.stderr[-4000:]
            or proc.stdout[-4000:]
            or "CANONICAL_RUNTIME_DID_NOT_COMPLETE"
        ),
    })
    emit(report)
    raise SystemExit(2)

model_counts = []
for raw in collect_named(state, "model_dependency_count"):
    try:
        model_counts.append(int(raw))
    except Exception:
        model_counts.append(-1)
report["observed_runtime_model_dependency_counts"] = model_counts
if any(x != 0 for x in model_counts):
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed":False,
        "independent_oracle_executed":False,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"COGNITION_PROVENANCE",
        "first_causal_blocker":"NONZERO_OR_INVALID_MODEL_DEPENDENCY_COUNT",
    })
    emit(report)
    raise SystemExit(3)

result_path = ROOT / RESULT_REL
result = safe_json(result_path) if result_path.is_file() else None
report["result_path"] = RESULT_REL
if not isinstance(result, dict):
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"INDEPENDENT_ORACLE_INPUT",
        "first_causal_blocker":"DECISION_QUALITY_RESULT_MISSING_OR_INVALID",
    })
    emit(report)
    raise SystemExit(4)

required_fields = list((task.get("required_output") or {}).get("fields") or [])
missing = [k for k in required_fields if k not in result]
if missing:
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"INDEPENDENT_ORACLE_INPUT",
        "first_causal_blocker":"REQUIRED_RESULT_FIELDS_MISSING",
        "missing_fields":missing,
    })
    emit(report)
    raise SystemExit(5)

try:
    v20 = numeric_value(result["viscosity_20c"])
    v40 = numeric_value(result["viscosity_40c"])
    ratio_claim = numeric_value(result["ratio_40c_to_20c"])
    producer_decision = decision_bool(result["decision"])
except Exception as exc:
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"INDEPENDENT_ORACLE_NUMERIC_PARSE",
        "first_causal_blocker":type(exc).__name__ + ":" + str(exc),
    })
    emit(report)
    raise SystemExit(6)

if not (v20 > 0 and v40 > 0):
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"INDEPENDENT_ORACLE_NUMERIC_SANITY",
        "first_causal_blocker":"NONPOSITIVE_VISCOSITY",
    })
    emit(report)
    raise SystemExit(7)

ratio_oracle = v40 / v20
ratio_ok = math.isclose(ratio_claim, ratio_oracle, rel_tol=2e-3, abs_tol=1e-8)
decision_oracle = ratio_oracle < 0.5
decision_ok = producer_decision == decision_oracle
result_model_count = result.get("model_dependency_count")
model_result_ok = result_model_count == 0

urls = collect_urls(result.get("source_provenance"))
if not urls:
    urls = collect_urls(result)
fetches = []
source_bodies = []
for url in urls[:8]:
    try:
        got = fetch_text(url)
        fetches.append({k:v for k,v in got.items() if k != "text"})
        if 200 <= got["status"] < 400:
            source_bodies.append(got["text"])
    except Exception as exc:
        fetches.append({"requested_url":url,"error":type(exc).__name__ + ":" + str(exc)})

joined = "\n".join(source_bodies).lower()
semantic_terms_ok = ("viscos" in joined and "water" in joined and re.search(r"\b20(?:\.0+)?\b", joined) and re.search(r"\b40(?:\.0+)?\b", joined))
value20_observed = any(tok in joined for tok in numeric_tokens(v20))
value40_observed = any(tok in joined for tok in numeric_tokens(v40))
source_semantics_ok = bool(source_bodies and semantic_terms_ok and value20_observed and value40_observed)

report["independent_oracle"] = {
    "producer_values":{"viscosity_20c":v20,"viscosity_40c":v40,"ratio_claim":ratio_claim,"decision":producer_decision},
    "recomputed_ratio_40c_to_20c":ratio_oracle,
    "recomputed_decision_less_than_half":decision_oracle,
    "ratio_matches":ratio_ok,
    "decision_matches":decision_ok,
    "result_model_dependency_zero":model_result_ok,
    "source_urls":urls[:8],
    "source_refetches":fetches,
    "source_semantics_water_viscosity_20c_40c":bool(semantic_terms_ok),
    "viscosity_20c_value_observed_in_refetched_source":value20_observed,
    "viscosity_40c_value_observed_in_refetched_source":value40_observed,
    "source_semantics_verified":source_semantics_ok,
    "producer_modules_imported":False,
}

if not (ratio_ok and decision_ok and model_result_ok and source_semantics_ok):
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "first_causal_stage":"INDEPENDENT_ORACLE_ASSERTIONS",
        "first_causal_blocker":"SOURCE_VALUE_OR_NUMERIC_DECISION_VERIFICATION_FAILED",
    })
    emit(report)
    raise SystemExit(8)

report.update({
    "status":"PASS_PRODUCER_AND_INDEPENDENT_ORACLE",
    "parent_task_completed":True,
    "independent_oracle_executed":True,
    "independent_oracle_verified":True,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
    "parent_capability_credit_authorized":False,
    "replay_allowed":False,
    "next_required_action":"RECONCILE_EXACT_RECEIPT_IN_CANONICAL_BRAIN_BEFORE_ANY_PARENT_CAPABILITY_CREDIT",
})
emit(report)
raise SystemExit(0)
