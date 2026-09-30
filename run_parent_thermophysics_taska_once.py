#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL = "canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_ID = "PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
RESULT_REL = "canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
REPORT_REL = "thermophysics-parent-taska-terminal.json"
REPORT_PATH = ROOT / REPORT_REL
STATE_PATH = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
EVID_DIR = ROOT / "canonical/astra_runtime/evidence"
RESULT_PATH = ROOT / RESULT_REL
BRAIN_MAIN = "fc07395c387563cbb2b3dfdc3b14fd80239a080b"

EXPECTED_BLOBS = {
    MISSION_REL: "982b883b353b937d8500bd9b70c1929c33313393",
    TASK_REL: "dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/capability_proposal_generators.py": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py": "6385b469f1287c971217dcac58af2ffebd81f9fd",
    "canonical/runtime/bound_capabilities/grounded_executable_composition.py": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
    "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
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

def urls_in(value):
    out = []
    if isinstance(value, str):
        out.extend(re.findall(r"https?://[^\s\]\[\)\(\}\{\"\']+", value))
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(urls_in(v))
    elif isinstance(value, list):
        for v in value:
            out.extend(urls_in(v))
    return sorted(set(out))

report = {
    "schema": "PROJECT_BRAIN_PARENT_THERMOPHYSICS_ONE_SHOT_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "task_path": TASK_REL,
    "result_path": RESULT_REL,
    "execution_count": 0,
    "task_executed": False,
    "same_task_replay_forbidden": True,
    "incremental_spend_usd": 0,
    "model_dependency_count": 0,
    "parent_capability_credit_delta": 0,
}

closure = {}
for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    closure[rel] = {"expected": expected, "observed": observed, "match": observed == expected}
report["closure"] = closure
if not all(x["match"] for x in closure.values()):
    report.update({
        "status": "PRESTART_CARRIER_CLOSURE_FAIL",
        "first_causal_blocker": "CARRIER_NOT_BYTE_IDENTICAL_TO_FROZEN_BRAIN_EXECUTION_CLOSURE",
    })
    emit(report)
    raise SystemExit(10)

mission = safe_json(ROOT / MISSION_REL)
task = safe_json(ROOT / TASK_REL)
if not isinstance(mission, dict) or not isinstance(task, dict):
    report.update({"status": "PRESTART_POLICY_FAIL", "first_causal_blocker": "FROZEN_TASK_OR_MISSION_INVALID_JSON"})
    emit(report)
    raise SystemExit(11)

mcon = mission.get("constraints") or {}
tcon = task.get("execution_constraints") or {}
anti = task.get("anti_leakage") or {}
contract_ok = (
    mission.get("mission_id") == MISSION_ID
    and task.get("task_id") == MISSION_ID
    and mission.get("goal") == task.get("goal_text")
    and mcon.get("model_dependency_count") == 0
    and mcon.get("incremental_spend_usd") == 0
    and mcon.get("model_planner_disabled") is True
    and mcon.get("fresh_parent_task") is True
    and mcon.get("exactly_one_execution") is True
    and tcon.get("model_dependency_count") == 0
    and tcon.get("incremental_spend_usd") == 0
    and tcon.get("exactly_one_execution") is True
    and tcon.get("stop_on_first_causal_gap") is True
    and tcon.get("direct_goal_compiler_harness_forbidden") is True
    and task.get("source_task_replay") is False
    and anti
    and not any(bool(v) for v in anti.values())
)
if not contract_ok:
    report.update({"status": "PRESTART_POLICY_FAIL", "first_causal_blocker": "FROZEN_PARENT_TASK_CONTRACT_INVALID"})
    emit(report)
    raise SystemExit(12)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({"status": "PRESTART_POLICY_FAIL", "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED"})
    emit(report)
    raise SystemExit(13)

contaminated = []
if STATE_PATH.exists():
    contaminated.append(str(STATE_PATH.relative_to(ROOT)))
if RESULT_PATH.exists():
    contaminated.append(str(RESULT_PATH.relative_to(ROOT)))
if EVID_DIR.exists():
    contaminated.extend(str(p.relative_to(ROOT)) for p in EVID_DIR.glob(MISSION_ID + "*"))
if contaminated:
    report.update({
        "status": "PRESTART_FRESHNESS_FAIL",
        "first_causal_blocker": "FROZEN_PARENT_TASK_ALREADY_HAS_RUNTIME_EVIDENCE",
        "contaminated_paths": sorted(set(contaminated)),
    })
    emit(report)
    raise SystemExit(14)

report["execution_count"] = 1
report["task_executed"] = True
proc = subprocess.run(
    [sys.executable, str(ROOT / "canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=900,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1", "PYTHONUNBUFFERED": "1"},
)

state = safe_json(STATE_PATH) if STATE_PATH.exists() else None
result = safe_json(RESULT_PATH) if RESULT_PATH.exists() else None
evidence = {}
if EVID_DIR.exists():
    for p in sorted(EVID_DIR.glob(MISSION_ID + "*")):
        if p.is_file():
            try:
                evidence[str(p.relative_to(ROOT))] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                evidence[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8", errors="replace")[-12000:]

combined = "\n".join([
    proc.stdout or "",
    proc.stderr or "",
    json.dumps(state, sort_keys=True, default=str) if state is not None else "",
    json.dumps(evidence, sort_keys=True, default=str),
])
report.update({
    "runtime_returncode": int(proc.returncode),
    "runtime_stdout_tail": (proc.stdout or "")[-16000:],
    "runtime_stderr_tail": (proc.stderr or "")[-16000:],
    "runtime_state": state,
    "evidence_paths": sorted(evidence.keys()),
    "producer_result": result,
})

blocker_markers = [
    "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH",
    "PLAIN_GOAL_BOUND_GROUNDING_FAILED",
    "GROUNDED_EXECUTABLE_COMPOSITION_FAILED",
    "CAPABILITY_DISCOVERY",
    "AUTO_CAPABILITY_ACQUISITION",
    "APT_ORIGIN_MISSION_PATH_INVALID",
    "PYPI_ORIGIN_MISSION_PATH_INVALID",
    "GOAL_ARCHITECTURAL_GAP",
    "BLOCKED",
]
observed_markers = [x for x in blocker_markers if x in combined]
report["observed_blocker_markers"] = observed_markers

producer_complete = proc.returncode == 0 and isinstance(result, dict)
if not producer_complete:
    report.update({
        "status": "PARENT_TASK_EXECUTED_ONCE__CAUSAL_GAP_CAPTURED",
        "first_causal_blocker": observed_markers[0] if observed_markers else "RUNTIME_NONZERO_OR_REQUIRED_RESULT_NOT_MATERIALIZED",
        "independent_oracle": {"status": "NOT_RUN__PRODUCER_DID_NOT_COMPLETE"},
        "next_required_action": "RECONCILE_FIRST_CAUSAL_GAP_IN_CANONICAL_BRAIN__DO_NOT_REPLAY_TASK",
    })
    emit(report)
    raise SystemExit(20)

oracle = {"status": "FAIL_CLOSED", "source_fetches": []}
try:
    v20 = float(result["viscosity_20c"])
    v40 = float(result["viscosity_40c"])
    claimed_ratio = float(result["ratio_40c_to_20c"])
    recomputed_ratio = v40 / v20
    ratio_match = abs(recomputed_ratio - claimed_ratio) <= max(1e-9, abs(recomputed_ratio) * 1e-6)
    expected_decision = recomputed_ratio < 0.5
    decision_text = str(result.get("decision", "")).lower()
    decision_match = (expected_decision and any(x in decision_text for x in ["yes", "true", "less than half"])) or ((not expected_decision) and any(x in decision_text for x in ["no", "false", "not less than half", "greater than", "more than half"]))
    urls = urls_in(result.get("source_provenance"))
    for url in urls[:8]:
        item = {"url": url}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-oracle/1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read(2_000_000)
                item.update({"ok": True, "status": getattr(resp, "status", 200), "sha256": sha256_bytes(raw), "bytes": len(raw)})
        except Exception as exc:
            item.update({"ok": False, "error": type(exc).__name__ + ":" + str(exc)})
        oracle["source_fetches"].append(item)
    sources_refetched = bool(oracle["source_fetches"]) and all(x.get("ok") for x in oracle["source_fetches"])
    oracle.update({
        "recomputed_ratio_40c_to_20c": recomputed_ratio,
        "claimed_ratio_40c_to_20c": claimed_ratio,
        "ratio_match": ratio_match,
        "expected_less_than_half": expected_decision,
        "decision_match": decision_match,
        "source_urls_found": urls,
        "sources_refetched": sources_refetched,
    })
    oracle["status"] = "PASS" if ratio_match and decision_match and sources_refetched else "INCOMPLETE_OR_FAILED"
except Exception as exc:
    oracle.update({"status": "ERROR", "error": type(exc).__name__ + ":" + str(exc)})

report["independent_oracle"] = oracle
if oracle.get("status") != "PASS":
    report.update({
        "status": "PRODUCER_COMPLETE__INDEPENDENT_ORACLE_NOT_PASSED",
        "first_causal_blocker": "INDEPENDENT_ORACLE_NOT_PASSED",
        "next_required_action": "RECONCILE_ORACLE_GAP_IN_CANONICAL_BRAIN__DO_NOT_REPLAY_TASK",
    })
    emit(report)
    raise SystemExit(21)

report.update({
    "status": "PARENT_TASK_EXECUTED_ONCE__PRODUCER_AND_INDEPENDENT_ORACLE_PASS",
    "first_causal_blocker": None,
    "parent_capability_credit_delta": 0,
    "next_required_action": "RECONCILE_VERIFIED_PARENT_RESULT_IN_CANONICAL_BRAIN__PROMOTION_ONLY_UNDER_EXISTING_LAWS",
})
emit(report)
raise SystemExit(0)
