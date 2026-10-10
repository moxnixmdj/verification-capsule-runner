#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SURFACE_PATH = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
INVARIANTS_PATH = "execution_guard/CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1.json"
RECEIPT = "TERMINAL_EXECUTION_ADMISSION_V4.json"
SCHEMA = "PROJECT_BRAIN_TERMINAL_EXECUTION_ADMISSION_V4"


class AdmissionError(RuntimeError):
    pass


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdmissionError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def safe_path(rel: str) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise AdmissionError("PATH_INVALID")
    path = (ROOT / rel).resolve()
    if path == ROOT or ROOT not in path.parents:
        raise AdmissionError("PATH_ESCAPE:" + rel)
    return path


def require_blob(rel: str, expected: str, errors: list[str]) -> None:
    try:
        path = safe_path(rel)
        if not path.is_file():
            errors.append("MISSING:" + rel)
        elif git_blob(path) != expected:
            errors.append("BLOB_MISMATCH:" + rel)
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))


def check_behavior(behavior: Mapping[str, Any], invariants: Mapping[str, Any], errors: list[str]) -> None:
    scope = behavior.get("scope")
    facts = behavior.get("behavior")
    if not isinstance(scope, str) or not isinstance(facts, Mapping):
        errors.append("BEHAVIOR_DOCUMENT_INVALID")
        return

    matched = 0
    for row in invariants.get("invariants", []):
        if not isinstance(row, Mapping) or row.get("scope") != scope:
            continue
        matched += 1
        req = row.get("requires")
        if not isinstance(req, Mapping):
            errors.append("INVARIANT_REQUIREMENTS_INVALID:" + str(row.get("id")))
            continue
        for key, expected in req.items():
            if facts.get(key) != expected:
                errors.append(f"INVARIANT_VIOLATION:{row.get('id')}:{key}")
    if matched == 0:
        errors.append("NO_ACTIVE_INVARIANT_FOR_SCOPE:" + str(scope))

    bindings = behavior.get("runtime_bindings")
    if not isinstance(bindings, Mapping):
        errors.append("BEHAVIOR_RUNTIME_BINDINGS_MISSING")
        return

    mandatory = {
        "planner", "agent", "prestart_guard", "transport", "zero_exposure_tests",
        "start_cas", "generic_start_cas", "identity_primitive", "start_barrier",
        "finalizer", "preflight", "admission_guard", "all_cycle_proof",
    }
    if facts.get("agent_ready_precedes_start_cas") is True:
        mandatory |= {
            "generic_status_store", "generic_ref_store", "causal_journal",
            "causal_journal_bridge", "status_journal_runner",
        }

    for key in sorted(mandatory):
        row = bindings.get(key)
        if not isinstance(row, Mapping):
            errors.append("BEHAVIOR_RUNTIME_BINDING_MISSING:" + key)
            continue
        rel, sha = row.get("path"), row.get("git_blob_sha")
        if not isinstance(rel, str) or not isinstance(sha, str):
            errors.append("BEHAVIOR_RUNTIME_BINDING_INVALID:" + key)
            continue
        require_blob(rel, sha, errors)

    # Every declared binding is authoritative; no unverified extras may hide in
    # the behavior document.
    for key, row in bindings.items():
        if not isinstance(row, Mapping):
            errors.append("BEHAVIOR_RUNTIME_BINDING_INVALID:" + str(key))
            continue
        rel, sha = row.get("path"), row.get("git_blob_sha")
        if isinstance(rel, str) and isinstance(sha, str):
            require_blob(rel, sha, errors)

    for key in (
        "all_cycle_context_fit_by_construction",
        "durable_start_cas_required",
        "task_start_defined_by_cas_acquisition",
        "aggregate_acceptance_credit_from_single_slot_forbidden",
    ):
        if facts.get(key) is not True:
            errors.append("BEHAVIOR_REQUIRED_FALSE:" + key)


def _runtime_marker(behavior: Mapping[str, Any], key: str) -> str:
    bindings = behavior.get("runtime_bindings")
    if not isinstance(bindings, Mapping):
        raise AdmissionError("BEHAVIOR_RUNTIME_BINDINGS_MISSING")
    row = bindings.get(key)
    if not isinstance(row, Mapping):
        raise AdmissionError("BEHAVIOR_RUNTIME_BINDING_MISSING:" + key)
    rel = row.get("path")
    if not isinstance(rel, str) or not rel:
        raise AdmissionError("BEHAVIOR_RUNTIME_BINDING_INVALID:" + key)
    return Path(rel).name


def check_workflow(text: str, behavior: Mapping[str, Any]) -> list[str]:
    """Validate phases from proof-carrying behavior, independent of shell quoting."""
    errors: list[str] = []
    facts = behavior.get("behavior")
    if not isinstance(facts, Mapping):
        return ["BEHAVIOR_FACTS_INVALID"]

    lines = text.splitlines()

    def line_pos(*tokens: str) -> int:
        for i, line in enumerate(lines):
            if all(token in line for token in tokens):
                return i
        return -1

    def line_count(*tokens: str) -> int:
        return sum(1 for line in lines if all(token in line for token in tokens))

    forbidden = {
        "PERSISTED_CHECKOUT_CREDENTIALS": ("persist-credentials: true",),
        "CONTENTS_WRITE_AUTHORITY": ("contents: write",),
        "V2_PRESTART": ("rank15_prestart_token_guard_v2.py",),
        "V2_AGENT": ("harbor_science_agent_v2:HarborScienceAgent",),
        "V2_FINALIZER": ("rank15_finalize_receipt_v2.py",),
    }
    for label, tokens in forbidden.items():
        if line_pos(*tokens) >= 0:
            errors.append("WORKFLOW_FORBIDDEN:" + label)

    try:
        start_cas = _runtime_marker(behavior, "start_cas")
        prestart = _runtime_marker(behavior, "prestart_guard")
        finalizer = _runtime_marker(behavior, "finalizer")
        delegated = facts.get("agent_ready_precedes_start_cas") is True
        status_runner = _runtime_marker(behavior, "status_journal_runner") if delegated else None
        agent_file = _runtime_marker(behavior, "agent")
        agent_marker = f"canonical.runtime.{Path(agent_file).stem}:HarborScienceAgent"
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))
        return sorted(set(errors))

    common_lines = [
        ("persist-credentials: false",),
        ("rm -rf llama.cpp",),
        ("git init llama.cpp",),
        ("cmake -S llama.cpp -B llama.cpp/build",),
        ("cmake --build llama.cpp/build",),
        ("http://127.0.0.1:8080/health",),
        ("SYNTHETIC_COMPLETION.json",),
        (start_cas, "--check-absent"),
        (prestart,),
        (finalizer,),
    ]
    for tokens in common_lines:
        if line_pos(*tokens) < 0:
            errors.append("WORKFLOW_REQUIRED_MARKER_MISSING:" + " + ".join(tokens))

    if delegated:
        if line_pos(status_runner) < 0:
            errors.append("WORKFLOW_REQUIRED_MARKER_MISSING:" + str(status_runner))
        for label, tokens in (
            ("DIRECT_START_ACQUIRE", (start_cas, "--acquire")),
            ("DIRECT_HARBOR_RUN", ("harbor run",)),
            ("DIRECT_AGENT_ENTRYPOINT", (agent_marker,)),
        ):
            if line_pos(*tokens) >= 0:
                errors.append("WORKFLOW_DELEGATION_BYPASS:" + label)
        order_tokens = [
            ("http://127.0.0.1:8080/health",),
            ("SYNTHETIC_COMPLETION.json",),
            (start_cas, "--check-absent"),
            (prestart,),
            (status_runner,),
            (finalizer,),
        ]
        if line_count(status_runner) != 1:
            errors.append("WORKFLOW_STATUS_RUNNER_COUNT_NOT_ONE")
    else:
        direct_required = [
            (start_cas, "--acquire"),
            (agent_marker,),
            ("harbor run",),
        ]
        for tokens in direct_required:
            if line_pos(*tokens) < 0:
                errors.append("WORKFLOW_REQUIRED_MARKER_MISSING:" + " + ".join(tokens))
        order_tokens = [
            ("http://127.0.0.1:8080/health",),
            ("SYNTHETIC_COMPLETION.json",),
            (start_cas, "--check-absent"),
            (prestart,),
            (start_cas, "--acquire"),
            ("harbor run",),
            (finalizer,),
        ]
        if line_count("harbor run") != 1:
            errors.append("WORKFLOW_HARBOR_RUN_COUNT_NOT_ONE")

    positions = [line_pos(*tokens) for tokens in order_tokens]
    if any(x < 0 for x in positions) or positions != sorted(positions):
        errors.append("WORKFLOW_PHASE_ORDER_INVALID")
    return sorted(set(errors))



def check_capability_first_admission(
    surface: Mapping[str, Any],
    *,
    workflow_rel: str,
    slot_id: str,
    task_digest: str,
) -> list[str]:
    errors: list[str] = []
    row = surface.get("capability_first_admission")
    if not isinstance(row, Mapping):
        return ["CAPABILITY_FIRST_ADMISSION_MISSING"]
    if row.get("schema") != "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V1":
        errors.append("CAPABILITY_FIRST_ADMISSION_SCHEMA_INVALID")
    if row.get("authorized") is not True:
        errors.append("CAPABILITY_FIRST_ADMISSION_NOT_AUTHORIZED")
    if row.get("workflow_path") != workflow_rel:
        errors.append("CAPABILITY_FIRST_ADMISSION_WORKFLOW_MISMATCH")
    if row.get("slot_id") != slot_id:
        errors.append("CAPABILITY_FIRST_ADMISSION_SLOT_MISMATCH")
    if row.get("task_digest") != task_digest:
        errors.append("CAPABILITY_FIRST_ADMISSION_TASK_DIGEST_MISMATCH")
    source = row.get("scheduler_source")
    if not isinstance(source, str) or not source:
        errors.append("CAPABILITY_FIRST_ADMISSION_SCHEDULER_SOURCE_MISSING")
    decision = row.get("decision")
    if decision != "ADMIT_CHECKPOINT_AUDIT_EXECUTION":
        errors.append("CAPABILITY_FIRST_ADMISSION_DECISION_INVALID")
    return sorted(set(errors))

def admission_errors(
    *, workflow_rel: str, slot_id: str, task_digest: str,
    require_activation: bool, require_execution_authority: bool,
) -> list[str]:
    errors: list[str] = []
    surface = read_json(safe_path(SURFACE_PATH))
    invariants = read_json(safe_path(INVARIANTS_PATH))
    if surface.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1":
        errors.append("SURFACE_SCHEMA_INVALID")
    if surface.get("active") is not True:
        errors.append("SURFACE_NOT_ACTIVE")
    if surface.get("workflow_path") != workflow_rel:
        errors.append("SURFACE_WORKFLOW_PATH_MISMATCH")
    if surface.get("slot_id") != slot_id or surface.get("task_digest") != task_digest:
        errors.append("SURFACE_SLOT_OR_DIGEST_MISMATCH")

    errors.extend(
        check_capability_first_admission(
            surface,
            workflow_rel=workflow_rel,
            slot_id=slot_id,
            task_digest=task_digest,
        )
    )

    workflow = safe_path(workflow_rel)
    if not workflow.is_file():
        errors.append("WORKFLOW_MISSING")
    else:
        expected = surface.get("workflow_git_blob_sha")
        if git_blob(workflow) != expected:
            errors.append("SURFACE_WORKFLOW_BLOB_MISMATCH")

    for key in ("behavior", "authority", "ledger", "invariant_registry", "admission_guard", "logical_attempt_claim_binding"):
        row = surface.get(key)
        if not isinstance(row, Mapping):
            errors.append("SURFACE_BINDING_MISSING:" + key)
            continue
        rel, sha = row.get("path"), row.get("git_blob_sha")
        if not isinstance(rel, str) or not isinstance(sha, str):
            errors.append("SURFACE_BINDING_INVALID:" + key)
        else:
            require_blob(rel, sha, errors)

    behavior_row = surface.get("behavior")
    if isinstance(behavior_row, Mapping) and isinstance(behavior_row.get("path"), str):
        behavior = read_json(safe_path(behavior_row["path"]))
        if behavior.get("slot_id") != slot_id or behavior.get("task_digest") != task_digest:
            errors.append("BEHAVIOR_SLOT_OR_DIGEST_MISMATCH")
        if behavior.get("workflow_path") != workflow_rel:
            errors.append("BEHAVIOR_WORKFLOW_MISMATCH")
        check_behavior(behavior, invariants, errors)
        if workflow.is_file():
            errors.extend(check_workflow(workflow.read_text(encoding="utf-8"), behavior))

    if require_activation:
        rel = surface.get("activation_path")
        if not isinstance(rel, str) or not safe_path(rel).is_file():
            errors.append("ACTIVATION_FILE_MISSING")
    if require_execution_authority and surface.get("execution_authority") is not True:
        errors.append("EXECUTION_AUTHORITY_NOT_ACTIVE")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--task-digest", required=True)
    parser.add_argument("--require-activation", action="store_true")
    parser.add_argument("--require-execution-authority", action="store_true")
    args = parser.parse_args()
    try:
        errors = admission_errors(
            workflow_rel=args.workflow,
            slot_id=args.slot,
            task_digest=args.task_digest,
            require_activation=args.require_activation,
            require_execution_authority=args.require_execution_authority,
        )
    except Exception as exc:
        errors = [type(exc).__name__ + ":" + str(exc)]
    out = {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "workflow": args.workflow,
        "slot_id": args.slot,
        "task_digest": args.task_digest,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    (ROOT / RECEIPT).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
