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
RECEIPT = "TERMINAL_EXECUTION_ADMISSION.json"
SCHEMA = "PROJECT_BRAIN_TERMINAL_EXECUTION_ADMISSION_V2"


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
    p = (ROOT / rel).resolve()
    if p == ROOT or ROOT not in p.parents:
        raise AdmissionError("PATH_ESCAPE:" + rel)
    return p


def require_blob(rel: str, expected: str, errors: list[str]) -> None:
    try:
        p = safe_path(rel)
        if not p.is_file():
            errors.append("MISSING:" + rel)
            return
        actual = git_blob(p)
        if actual != expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))


def check_behavior_against_invariants(
    behavior_doc: Mapping[str, Any],
    invariant_doc: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    scope = behavior_doc.get("scope")
    behavior = behavior_doc.get("behavior")
    if not isinstance(scope, str) or not isinstance(behavior, Mapping):
        return ["BEHAVIOR_DOCUMENT_INVALID"]

    matched = 0
    rows = invariant_doc.get("invariants")
    if not isinstance(rows, list):
        return ["INVARIANT_SET_INVALID"]
    for row in rows:
        if not isinstance(row, Mapping) or row.get("scope") != scope:
            continue
        matched += 1
        req = row.get("requires")
        if not isinstance(req, Mapping):
            errors.append("INVARIANT_REQUIREMENTS_INVALID:" + str(row.get("id")))
            continue
        for key, expected in req.items():
            if behavior.get(key) != expected:
                errors.append(
                    f"INVARIANT_VIOLATION:{row.get('id')}:{key}:"
                    f"{behavior.get(key)!r}!={expected!r}"
                )
    if matched == 0:
        errors.append("NO_ACTIVE_INVARIANT_FOR_SCOPE:" + scope)
    return errors


def check_runtime_bindings(
    behavior_doc: Mapping[str, Any],
    errors: list[str],
) -> None:
    bindings = behavior_doc.get("runtime_bindings")
    required = {
        "planner",
        "agent",
        "prestart_guard",
        "transport",
        "zero_exposure_tests",
        "start_cas",
        "start_cas_tests",
        "finalizer",
    }
    if not isinstance(bindings, Mapping):
        errors.append("BEHAVIOR_RUNTIME_BINDINGS_MISSING")
        return
    missing = sorted(required - set(bindings))
    if missing:
        errors.append("BEHAVIOR_RUNTIME_BINDINGS_INCOMPLETE:" + ",".join(missing))
    unknown = sorted(set(bindings) - required)
    if unknown:
        errors.append("BEHAVIOR_RUNTIME_BINDINGS_UNKNOWN:" + ",".join(unknown))
    for key in sorted(required):
        row = bindings.get(key)
        if not isinstance(row, Mapping):
            errors.append("BEHAVIOR_RUNTIME_BINDING_INVALID:" + key)
            continue
        rel = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(rel, str) or not isinstance(sha, str):
            errors.append("BEHAVIOR_RUNTIME_BINDING_INVALID:" + key)
            continue
        require_blob(rel, sha, errors)


def check_rank15_v3_workflow_text(text: str) -> list[str]:
    errors: list[str] = []
    forbidden = {
        "COMPILED_LLAMA_CACHE_KEY": "brain-llama-cpp",
        "COMPILED_LLAMA_CACHE_PATH": "path: llama.cpp\n",
        "PERSISTED_CHECKOUT_CREDENTIALS": "persist-credentials: true",
        "V2_AGENT_ROUTE": "canonical.runtime.harbor_science_agent_v2:HarborScienceAgent",
        "V2_PRESTART_ROUTE": "rank15_prestart_token_guard_v2.py",
    }
    for label, marker in forbidden.items():
        if marker in text:
            errors.append("WORKFLOW_FORBIDDEN:" + label)

    required = [
        "persist-credentials: false",
        "rm -rf llama.cpp",
        "git init llama.cpp",
        "git -C llama.cpp fetch --depth 1 origin",
        "rm -rf llama.cpp/build",
        "cmake -S llama.cpp -B llama.cpp/build",
        "cmake --build llama.cpp/build",
        "echo $! > LOCAL_QWEN_SERVER.pid",
        'kill -0 "$(cat LOCAL_QWEN_SERVER.pid)"',
        "http://127.0.0.1:8080/health",
        "SYNTHETIC_COMPLETION.json",
        "rank15_prestart_token_guard_v3.py",
        "RANK15_START_INTENT.json",
        "terminal_slot_start_cas_v1.py",
        "TERMINAL_SLOT_START_CAS_RECEIPT.json",
        "canonical.runtime.harbor_science_agent_v3:HarborScienceAgent",
        "rank15_finalize_receipt_v3.py",
        "harbor run",
    ]
    for marker in required:
        if marker not in text:
            errors.append("WORKFLOW_REQUIRED_MARKER_MISSING:" + marker)

    order = [
        "rm -rf llama.cpp",
        "cmake -S llama.cpp -B llama.cpp/build",
        "nohup llama.cpp/build/bin/llama-server",
        "http://127.0.0.1:8080/health",
        "SYNTHETIC_COMPLETION.json",
        "rank15_prestart_token_guard_v3.py",
        "RANK15_START_INTENT.json",
        "terminal_slot_start_cas_v1.py",
        "harbor run",
    ]
    positions = [text.find(x) for x in order]
    if any(p < 0 for p in positions) or positions != sorted(positions):
        errors.append("WORKFLOW_PHASE_ORDER_INVALID")

    if text.count("harbor run") != 1:
        errors.append("WORKFLOW_HARBOR_RUN_COUNT_NOT_ONE")
    if "permissions:\n  contents: write" not in text:
        errors.append("WORKFLOW_START_CAS_WRITE_PERMISSION_MISSING")
    return errors


def admission_errors(
    *,
    workflow_rel: str,
    slot_id: str,
    task_digest: str,
    require_activation: bool,
    require_execution_authority: bool,
) -> list[str]:
    errors: list[str] = []

    surface = read_json(safe_path(SURFACE_PATH))
    invariants = read_json(safe_path(INVARIANTS_PATH))

    if surface.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1":
        errors.append("SURFACE_SCHEMA_INVALID")
    if invariants.get("schema") != "PROJECT_BRAIN_CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1":
        errors.append("INVARIANT_SCHEMA_INVALID")
    if surface.get("active") is not True:
        errors.append("SURFACE_NOT_ACTIVE")

    if surface.get("workflow_path") != workflow_rel:
        errors.append("SURFACE_WORKFLOW_PATH_MISMATCH")
    if surface.get("slot_id") != slot_id:
        errors.append("SURFACE_SLOT_MISMATCH")
    if surface.get("task_digest") != task_digest:
        errors.append("SURFACE_TASK_DIGEST_MISMATCH")

    workflow_path = safe_path(workflow_rel)
    if not workflow_path.is_file():
        errors.append("WORKFLOW_MISSING")
        workflow_text = ""
    else:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        expected = surface.get("workflow_git_blob_sha")
        if git_blob(workflow_path) != expected:
            errors.append("SURFACE_WORKFLOW_BLOB_MISMATCH")
        errors.extend(check_rank15_v3_workflow_text(workflow_text))

    for key in (
        "behavior",
        "authority",
        "ledger",
        "invariant_registry",
        "admission_guard",
        "start_cas",
        "all_cycle_verification",
        "finalizer",
    ):
        row = surface.get(key)
        if not isinstance(row, Mapping):
            errors.append("SURFACE_BINDING_MISSING:" + key)
            continue
        rel = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(rel, str) or not isinstance(sha, str):
            errors.append("SURFACE_BINDING_INVALID:" + key)
            continue
        require_blob(rel, sha, errors)

    behavior_row = surface.get("behavior")
    if isinstance(behavior_row, Mapping) and isinstance(behavior_row.get("path"), str):
        try:
            behavior_doc = read_json(safe_path(behavior_row["path"]))
            if behavior_doc.get("slot_id") != slot_id:
                errors.append("BEHAVIOR_SLOT_MISMATCH")
            if behavior_doc.get("task_digest") != task_digest:
                errors.append("BEHAVIOR_TASK_DIGEST_MISMATCH")
            if behavior_doc.get("workflow_path") != workflow_rel:
                errors.append("BEHAVIOR_WORKFLOW_MISMATCH")
            errors.extend(check_behavior_against_invariants(behavior_doc, invariants))
            check_runtime_bindings(behavior_doc, errors)
            behavior = behavior_doc.get("behavior") if isinstance(behavior_doc, Mapping) else {}
            extra = {
                "all_cycle_fit_by_construction": True,
                "durable_slot_start_cas_required": True,
                "prestart_receipt_bound_to_start_intent": True,
                "start_cas_key_excludes_carrier_identity": True,
                "start_cas_replay_authority": False,
                "start_cas_replacement_carrier_authority": False,
                "single_slot_aggregate_acceptance_credit": False,
            }
            for key, expected in extra.items():
                if not isinstance(behavior, Mapping) or behavior.get(key) != expected:
                    errors.append(
                        f"V3_COMPOSITION_INVARIANT_VIOLATION:{key}:"
                        f"{behavior.get(key) if isinstance(behavior, Mapping) else None!r}!={expected!r}"
                    )
        except Exception as exc:
            errors.append("BEHAVIOR_READ_FAILED:" + type(exc).__name__ + ":" + str(exc))

    registry_binding = surface.get("invariant_registry")
    if isinstance(registry_binding, Mapping):
        if registry_binding.get("path") != INVARIANTS_PATH:
            errors.append("INVARIANT_REGISTRY_PATH_MISMATCH")
        if registry_binding.get("git_blob_sha") != git_blob(safe_path(INVARIANTS_PATH)):
            errors.append("INVARIANT_REGISTRY_BLOB_MISMATCH")

    for row in invariants.get("invariants", []):
        if not isinstance(row, Mapping):
            continue
        proof = row.get("proof")
        if not isinstance(proof, Mapping):
            errors.append("INVARIANT_PROOF_MISSING:" + str(row.get("id")))
            continue
        for prefix in ("repair", "independent_verification"):
            rel = proof.get(prefix + "_path")
            sha = proof.get(prefix + "_git_blob_sha")
            if not isinstance(rel, str) or not isinstance(sha, str):
                errors.append("INVARIANT_PROOF_BINDING_INVALID:" + str(row.get("id")) + ":" + prefix)
                continue
            require_blob(rel, sha, errors)

    if require_activation:
        activation_rel = surface.get("activation_path")
        if not isinstance(activation_rel, str):
            errors.append("ACTIVATION_PATH_MISSING")
        else:
            p = safe_path(activation_rel)
            if not p.is_file():
                errors.append("ACTIVATION_FILE_MISSING")

    if require_execution_authority and surface.get("execution_authority") is not True:
        errors.append("EXECUTION_AUTHORITY_NOT_ACTIVE")

    return sorted(set(errors))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--slot", required=True)
    ap.add_argument("--task-digest", required=True)
    ap.add_argument("--require-activation", action="store_true")
    ap.add_argument("--require-execution-authority", action="store_true")
    args = ap.parse_args()

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
        "execution_authority_required": args.require_execution_authority,
        "activation_required": args.require_activation,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "incremental_spend_usd": 0,
        "terminal_credit_delta": 0,
    }
    (ROOT / RECEIPT).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
