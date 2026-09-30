#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/PARENT_OPEN_ENDED_CO2_AUTHORITY_REAL_TASK_20260930_001.json"
MISSION_PATH = ROOT / MISSION_REL
REPORT_PATH = ROOT / "ca16-worldbank-openended-taska-terminal.json"
MISSION_ID = "PARENT-OPEN-ENDED-CO2-AUTHORITY-REAL-TASK-20260930-001"
BRAIN_MAIN = "ca16a72e8e83f5274b04265fe02eb7729451da93"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    MISSION_REL: "d4e9389c02702cfec6910c7a7c662bc6421dd392",
}

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def find_key_values(value, key):
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                found.append(v)
            found.extend(find_key_values(v, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(find_key_values(item, key))
    return found

def host_within(host, domain):
    host = str(host or "").lower().strip(".")
    domain = str(domain or "").lower().strip(".")
    return bool(host and domain and (host == domain or host.endswith("." + domain)))

def independent_fetch(url, timeout=25, max_bytes=2500000):
    req = urllib.request.Request(
        str(url),
        headers={"User-Agent": "ProjectBrain-Independent-TaskA-Oracle/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(max_bytes)
        final_url = resp.geturl()
        status = int(getattr(resp, "status", 200))
        content_type = str(resp.headers.get("Content-Type") or "")
    return {
        "requested_url": str(url),
        "final_url": str(final_url),
        "status": status,
        "content_type": content_type,
        "sha256": sha256_bytes(raw),
        "body": raw.decode("utf-8", "replace"),
    }

report = {
    "schema": "PROJECT_BRAIN_CA16_OPEN_ENDED_TASK_A_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "mission_id": MISSION_ID,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
    "same_task_replay_forbidden": True,
}

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    observed = git_blob_sha(path) if path.is_file() else None
    if observed != expected:
        report.update({
            "status": "CARRIER_CLOSURE_FAIL",
            "path": rel,
            "expected_blob": expected,
            "observed_blob": observed,
            "execution_count": 0,
            "task_executed": False,
            "replay_allowed": True,
            "replay_reason": "PRESTART_CARRIER_CLOSURE_FAILURE",
        })
        emit(report)
        raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MODEL_PLANNER_NOT_DISABLED",
        "execution_count": 0,
        "task_executed": False,
        "replay_allowed": True,
        "replay_reason": "PRESTART_POLICY_FAILURE",
    })
    emit(report)
    raise SystemExit(1)

mission = safe_json(MISSION_PATH)
if not isinstance(mission, dict) or mission.get("mission_id") != MISSION_ID:
    report.update({
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MISSION_ID_OR_JSON_INVALID",
        "execution_count": 0,
        "task_executed": False,
        "replay_allowed": True,
        "replay_reason": "PRESTART_MISSION_VALIDATION_FAILURE",
    })
    emit(report)
    raise SystemExit(1)

constraints = mission.get("constraints") or {}
required_true = (
    "no_frontier_model_cognition",
    "hand_authored_controller_actions_forbidden",
    "plain_goal_compilation_required",
    "autonomous_decomposition_required",
    "autonomous_material_source_or_tool_discovery_required",
    "independent_verification_required",
    "exactly_one_execution",
    "same_task_replay_forbidden",
    "stop_on_first_causal_gap",
)
if (
    constraints.get("incremental_spend_usd") != 0
    or constraints.get("model_dependency_count") != 0
    or any(constraints.get(k) is not True for k in required_true)
    or constraints.get("authority_domain_predeclared") is not False
    or constraints.get("source_url_predeclared") is not False
    or constraints.get("complete_research_plan_predeclared_to_producer") is not False
):
    report.update({
        "status": "CARRIER_POLICY_FAIL",
        "first_causal_blocker": "MISSION_CONSTRAINT_CONTRACT_INVALID",
        "execution_count": 0,
        "task_executed": False,
        "replay_allowed": True,
        "replay_reason": "PRESTART_MISSION_CONTRACT_FAILURE",
    })
    emit(report)
    raise SystemExit(1)

tmp_dir = ROOT / "canonical" / "astra_runtime" / "tmp"
before = {
    str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes())
    for p in tmp_dir.glob("AUTHORITY_SOURCE_*")
    if p.is_file()
} if tmp_dir.is_dir() else {}

report["execution_count"] = 1
report["task_executed"] = True
proc = subprocess.run(
    [
        sys.executable,
        str(ROOT / "canonical/runtime/astra_runtime.py"),
        MISSION_REL,
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=600,
    env={**os.environ, "ASTRA_DISABLE_MODEL_PLANNER": "1"},
)
report["producer_returncode"] = int(proc.returncode)
report["producer_stdout_tail"] = proc.stdout[-12000:]
report["producer_stderr_tail"] = proc.stderr[-12000:]

state_path = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
state = safe_json(state_path) if state_path.is_file() else None
report["state_path"] = str(state_path.relative_to(ROOT))
report["producer_state"] = state

after_files = {}
if tmp_dir.is_dir():
    for p in tmp_dir.glob("AUTHORITY_SOURCE_*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        digest = sha256_bytes(p.read_bytes())
        if before.get(rel) != digest:
            after_files[rel] = digest
report["new_or_changed_authority_artifacts"] = after_files

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
            or proc.stderr[-3000:]
            or proc.stdout[-3000:]
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

model_counts = []
for raw in find_key_values(state, "model_dependency_count"):
    try:
        model_counts.append(int(raw))
    except Exception:
        model_counts.append(-1)
report["observed_model_dependency_counts"] = model_counts
if model_counts and any(v != 0 for v in model_counts):
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
    raise SystemExit(4)

identity_candidates = sorted(tmp_dir.glob("AUTHORITY_SOURCE_*_IDENTITY.json")) if tmp_dir.is_dir() else []
discovery_candidates = sorted(tmp_dir.glob("AUTHORITY_SOURCE_*_DISCOVERY.json")) if tmp_dir.is_dir() else []
source_candidates = sorted(tmp_dir.glob("AUTHORITY_SOURCE_*_SOURCE_RENDER.json")) if tmp_dir.is_dir() else []
identity_candidates = [p for p in identity_candidates if str(p.relative_to(ROOT)) in after_files]
discovery_candidates = [p for p in discovery_candidates if str(p.relative_to(ROOT)) in after_files]
source_candidates = [p for p in source_candidates if str(p.relative_to(ROOT)) in after_files]

if len(identity_candidates) != 1 or len(discovery_candidates) != 1 or len(source_candidates) != 1:
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "INDEPENDENT_ORACLE_INPUT_DISCOVERY",
        "first_causal_blocker": "EXPECTED_EXACTLY_ONE_NEW_AUTHORITY_ARTIFACT_SET",
        "oracle_artifact_counts": {
            "identity": len(identity_candidates),
            "discovery": len(discovery_candidates),
            "source_render": len(source_candidates),
        },
    })
    emit(report)
    raise SystemExit(5)

identity = safe_json(identity_candidates[0])
discovery = safe_json(discovery_candidates[0])
source_render = safe_json(source_candidates[0])
if not all(isinstance(x, dict) for x in (identity, discovery, source_render)):
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "INDEPENDENT_ORACLE_INPUT_PARSE",
        "first_causal_blocker": "AUTHORITY_ARTIFACT_JSON_INVALID",
    })
    emit(report)
    raise SystemExit(6)

authority_domain = str(identity.get("authority_domain") or "").lower()
official_url = str(identity.get("official_url") or identity.get("final_url") or "")
chosen_url = str(discovery.get("chosen_url") or "")
producer_source_url = str(source_render.get("final_url") or chosen_url)
oracle = {
    "producer_identity_path": str(identity_candidates[0].relative_to(ROOT)),
    "producer_discovery_path": str(discovery_candidates[0].relative_to(ROOT)),
    "producer_source_render_path": str(source_candidates[0].relative_to(ROOT)),
    "authority_domain": authority_domain,
    "official_url": official_url,
    "chosen_url": chosen_url,
    "producer_source_url": producer_source_url,
}

try:
    official = independent_fetch(official_url)
    source = independent_fetch(chosen_url)
except Exception as exc:
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "INDEPENDENT_ORACLE_REFETCH",
        "first_causal_blocker": type(exc).__name__ + ":" + str(exc),
        "independent_oracle": oracle,
    })
    emit(report)
    raise SystemExit(7)

official_host = (urllib.parse.urlparse(official["final_url"]).hostname or "").lower()
source_host = (urllib.parse.urlparse(source["final_url"]).hostname or "").lower()
source_body_lower = source["body"].lower()
source_body_normalized = re.sub(r"[^a-z0-9]+", "", source_body_lower)
indicator_exact = "en.atm.co2e.pc" in source_body_lower
indicator_normalized = "enatmco2epc" in source_body_normalized
world_bank_tokens = [t for t in ("world", "bank") if t in official["body"].lower()]

oracle.update({
    "official_refetch": {k:v for k,v in official.items() if k != "body"},
    "source_refetch": {k:v for k,v in source.items() if k != "body"},
    "official_host_within_authority_domain": host_within(official_host, authority_domain),
    "source_host_within_authority_domain": host_within(source_host, authority_domain),
    "official_world_bank_tokens": world_bank_tokens,
    "indicator_exact_present": indicator_exact,
    "indicator_normalized_present": indicator_normalized,
})
report["independent_oracle"] = oracle

oracle_ok = (
    bool(authority_domain)
    and host_within(official_host, authority_domain)
    and host_within(source_host, authority_domain)
    and len(world_bank_tokens) == 2
    and (indicator_exact or indicator_normalized)
)
if not oracle_ok:
    report.update({
        "status": "FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed": False,
        "independent_oracle_executed": True,
        "parent_capability_credit_authorized": False,
        "replay_allowed": False,
        "first_causal_stage": "INDEPENDENT_ORACLE_ASSERTIONS",
        "first_causal_blocker": "AUTHORITY_OR_INDICATOR_SEMANTIC_ASSERTION_FAILED",
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
