#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import rank20_start_cas_v7 as start_cas

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK20_V7"
SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
TASK = "terminal-bench-science/hysteretic-aquifer-control"
DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _git_blob(path: Path) -> str | None:
    if not path.is_file():
        return None
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _slot_start_key() -> str:
    material = json.dumps(
        {"slot_id": SLOT, "task_digest": DIGEST},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "terminal-start/" + hashlib.sha256(material.encode()).hexdigest()


def _hex(value: Any, n: int) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % n, value) is not None


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    safe_id = os.environ.get("SAFE_ID") or "hysteretic-aquifer-control-trial-0"
    base = root / "jobs" / safe_id
    guard_path = root / "RANK20_PRESTART_GUARD.json"
    cas_path = root / "RANK20_START_CAS_V7.json"
    guard = _read_json(guard_path)
    cas = _read_json(cas_path)
    surface_path = root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
    surface = _read_json(surface_path)

    cas_claimed_acquired = (
        cas.get("pass") is True
        and cas.get("acquired") is True
        and cas.get("task_started") is True
        and cas.get("slot_id") == SLOT
        and cas.get("task_digest") == DIGEST
    )

    cas_binding_errors: list[str] = []
    if cas_claimed_acquired:
        expected_prestart_sha = _sha256(guard_path)
        expected_logical = guard.get("logical_attempt_id")
        runtime_material = cas.get("runtime_identity_material")
        expected_runtime_sha = None
        expected_runtime_material = None
        runtime_recompute_error = None
        try:
            expected_runtime_sha, expected_runtime_material = start_cas._runtime_identity(root, surface)
        except Exception as exc:
            runtime_recompute_error = type(exc).__name__ + ":" + str(exc)

        workflow_rel = surface.get("workflow_path") if isinstance(surface, dict) else None
        workflow_expected = surface.get("workflow_git_blob_sha") if isinstance(surface, dict) else None
        workflow_actual = (
            _git_blob(root / workflow_rel)
            if isinstance(workflow_rel, str)
            else None
        )
        authority_row = surface.get("authority") if isinstance(surface, dict) else None
        authority_rel = authority_row.get("path") if isinstance(authority_row, dict) else None
        authority_expected = authority_row.get("git_blob_sha") if isinstance(authority_row, dict) else None
        authority_actual = (
            _git_blob(root / authority_rel)
            if isinstance(authority_rel, str)
            else None
        )
        activation_rel = surface.get("activation_path") if isinstance(surface, dict) else None
        activation_actual = (
            _git_blob(root / activation_rel)
            if isinstance(activation_rel, str)
            else None
        )

        epoch_row = surface.get("epoch") if isinstance(surface, dict) else None
        claim_row = surface.get("execution_claim") if isinstance(surface, dict) else None
        epoch_rel = epoch_row.get("path") if isinstance(epoch_row, dict) else None
        claim_rel = claim_row.get("path") if isinstance(claim_row, dict) else None
        epoch_expected = epoch_row.get("git_blob_sha") if isinstance(epoch_row, dict) else None
        claim_expected = claim_row.get("git_blob_sha") if isinstance(claim_row, dict) else None
        epoch_actual = _git_blob(root / epoch_rel) if isinstance(epoch_rel, str) else None
        claim_actual = _git_blob(root / claim_rel) if isinstance(claim_rel, str) else None
        checks = {
            "GENERIC_CAS_KEY": cas.get("generic_cas_key") == _slot_start_key(),
            "LOGICAL_ATTEMPT_ID_FORMAT": _hex(cas.get("logical_attempt_id"), 64),
            "LOGICAL_ATTEMPT_ID_MATCH": (
                isinstance(expected_logical, str)
                and cas.get("logical_attempt_id") == expected_logical
            ),
            "RUNTIME_IDENTITY_FORMAT": _hex(cas.get("runtime_identity_sha256"), 64),
            "RUNTIME_IDENTITY_RECOMPUTE_OK": runtime_recompute_error is None,
            "RUNTIME_IDENTITY_RECOMPUTED_MATCH": (
                expected_runtime_sha is not None
                and cas.get("runtime_identity_sha256") == expected_runtime_sha
            ),
            "RUNTIME_IDENTITY_MATERIAL_EXACT_MATCH": (
                isinstance(runtime_material, dict)
                and expected_runtime_material is not None
                and runtime_material == expected_runtime_material
            ),
            "WORKFLOW_SURFACE_BINDING_VALID": (
                isinstance(workflow_expected, str)
                and workflow_actual == workflow_expected
            ),
            "WORKFLOW_CAS_MATCH": (
                isinstance(workflow_expected, str)
                and cas.get("workflow_git_blob_sha") == workflow_expected
            ),
            "AUTHORITY_SURFACE_BINDING_VALID": (
                isinstance(authority_expected, str)
                and authority_actual == authority_expected
            ),
            "AUTHORITY_CAS_MATCH": (
                isinstance(authority_expected, str)
                and cas.get("authority_git_blob_sha") == authority_expected
            ),
            "ACTIVATION_CAS_MATCH": (
                activation_actual is not None
                and cas.get("activation_git_blob_sha") == activation_actual
            ),
            "PRESTART_RECEIPT_SHA_FORMAT": _hex(cas.get("prestart_receipt_sha256"), 64),
            "PRESTART_RECEIPT_SHA_MATCH": (
                expected_prestart_sha is not None
                and cas.get("prestart_receipt_sha256") == expected_prestart_sha
            ),
            "DURABLE_RECORD_SHA_FORMAT": _hex(cas.get("durable_record_sha256"), 64),
            "WORKFLOW_BLOB_FORMAT": _hex(cas.get("workflow_git_blob_sha"), 40),
            "AUTHORITY_BLOB_FORMAT": _hex(cas.get("authority_git_blob_sha"), 40),
            "ACTIVATION_BLOB_FORMAT": _hex(cas.get("activation_git_blob_sha"), 40),
            "REPLAY_AUTHORITY_FALSE": cas.get("replay_authority") is False,
            "REPLACEMENT_AUTHORITY_FALSE": cas.get("replacement_carrier_authority") is False,
            "RUNTIME_IDENTITY_MATERIAL_OBJECT": isinstance(runtime_material, dict),
            "EPOCH_SURFACE_BINDING_VALID": (
                isinstance(epoch_expected, str)
                and epoch_actual == epoch_expected
            ),
            "CLAIM_SURFACE_BINDING_VALID": (
                isinstance(claim_expected, str)
                and claim_actual == claim_expected
            ),
            "RUNTIME_IDENTITY_EPOCH_MATCH": (
                isinstance(runtime_material, dict)
                and runtime_material.get("epoch_git_blob_sha") == epoch_expected
            ),
            "RUNTIME_IDENTITY_CLAIM_MATCH": (
                isinstance(runtime_material, dict)
                and runtime_material.get("execution_claim_git_blob_sha") == claim_expected
            ),
        }
        cas_binding_errors = [
            "START_CAS_IDENTITY_INVALID:" + label
            for label, passed in checks.items()
            if not passed
        ]
    cas_identity_valid = cas_claimed_acquired and not cas_binding_errors

    # CAS acquisition is the irreversible accounting boundary. A malformed or
    # partially lost local identity receipt can never restore retry authority.
    task_started = cas_claimed_acquired

    results: list[tuple[Path, dict[str, Any]]] = []
    if base.exists():
        for path in base.rglob("result.json"):
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(obj, dict):
                results.append((path, obj))

    scored: list[tuple[Path, dict[str, Any]]] = []
    exception_info: list[dict[str, Any]] = []
    for path, obj in results:
        vr = obj.get("verifier_result")
        if isinstance(vr, dict) and isinstance(vr.get("rewards"), dict):
            scored.append((path, obj))
        ex = obj.get("exception_info")
        if isinstance(ex, dict):
            exception_info.append({
                "path": str(path.relative_to(root)),
                "exception_type": ex.get("exception_type"),
                "exception_message": ex.get("exception_message"),
            })

    reward = None
    errors: list[str] = list(cas_binding_errors)
    if task_started:
        if len(scored) == 1:
            raw = scored[0][1]["verifier_result"]["rewards"].get("reward")
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                reward = float(raw)
            else:
                errors.append("REWARD_MISSING_OR_NONNUMERIC")
        elif not scored:
            errors.append("NO_TRIAL_RESULT_WITH_VERIFIER_REWARD")
        else:
            errors.append("MULTIPLE_TRIAL_RESULTS_WITH_VERIFIER_REWARD")

    carrier_ready = os.environ.get("CACHE_READY") == "true"
    harbor_outcome = os.environ.get("HARBOR_OUTCOME") or "skipped"
    success = (
        task_started
        and cas_identity_valid
        and reward is not None
        and reward >= 1.0
        and not errors
    )

    if not task_started:
        errors = ["TASK_NOT_STARTED__NO_DURABLE_START_CAS"]
        status = "PREEXPOSURE_ABORT_NONCONSUMING"
    else:
        status = "SUCCESS" if success else "FINAL_ZERO"

    hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path, _ in results
    }
    receipt = {
        "schema": SCHEMA,
        "slot_id": SLOT,
        "task_name": TASK,
        "task_digest": DIGEST,
        "status": status,
        "reward": None if not task_started else (reward if reward is not None else 0.0),
        "carrier_ready": carrier_ready,
        "task_read": bool(guard.get("task_read")),
        "task_started": task_started,
        "start_cas_acquired": cas_claimed_acquired,
        "start_cas_identity_valid": cas_identity_valid,
        "start_cas_status": cas.get("status"),
        "start_cas_generic_key": cas.get("generic_cas_key"),
        "start_cas_logical_attempt_id": cas.get("logical_attempt_id"),
        "start_cas_runtime_identity_sha256": cas.get("runtime_identity_sha256"),
        "start_cas_runtime_identity_material": cas.get("runtime_identity_material"),
        "recomputed_runtime_identity_sha256": expected_runtime_sha if cas_claimed_acquired else None,
        "runtime_identity_recompute_error": runtime_recompute_error if cas_claimed_acquired else None,
        "surface_workflow_git_blob_sha": workflow_expected if cas_claimed_acquired else None,
        "surface_authority_git_blob_sha": authority_expected if cas_claimed_acquired else None,
        "surface_activation_git_blob_sha": activation_actual if cas_claimed_acquired else None,
        "surface_epoch_git_blob_sha": (
            surface.get("epoch", {}).get("git_blob_sha")
            if isinstance(surface.get("epoch"), dict) else None
        ),
        "surface_execution_claim_git_blob_sha": (
            surface.get("execution_claim", {}).get("git_blob_sha")
            if isinstance(surface.get("execution_claim"), dict) else None
        ),
        "start_cas_prestart_receipt_sha256": cas.get("prestart_receipt_sha256"),
        "start_cas_durable_record_sha256": cas.get("durable_record_sha256"),
        "start_cas_workflow_git_blob_sha": cas.get("workflow_git_blob_sha"),
        "start_cas_authority_git_blob_sha": cas.get("authority_git_blob_sha"),
        "start_cas_activation_git_blob_sha": cas.get("activation_git_blob_sha"),
        "start_cas_replay_authority": cas.get("replay_authority"),
        "start_cas_replacement_carrier_authority": cas.get("replacement_carrier_authority"),
        "prestart_guard_sha256": _sha256(guard_path),
        "prestart_guard_status": guard.get("status"),
        "prestart_guard_pass": guard.get("pass"),
        "prestart_input_tokens": guard.get("input_tokens"),
        "prestart_context_headroom_tokens": guard.get("context_headroom_tokens"),
        "prestart_instruction_sha256": guard.get("instruction_sha256"),
        "prestart_first_cycle_prompt_sha256": guard.get("first_cycle_prompt_sha256"),
        "prestart_logical_attempt_id": guard.get("logical_attempt_id"),
        "prestart_payload_sha256": guard.get("payload_sha256"),
        "prestart_request_identity_sha256": guard.get("request_identity_sha256"),
        "raw_task_obligation_count": guard.get("raw_task_obligation_count"),
        "errors": errors,
        "exception_info": exception_info,
        "harbor_step_outcome": harbor_outcome,
        "result_hashes": hashes,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "execution_authority_consumed": task_started,
        "benchmark_trials_consumed": 1 if task_started else 0,
        "consumed_successes_delta": 1 if success else 0,
        "consumed_final_failures_delta": 1 if task_started and not success else 0,
        "rerun_credit": False,
        "incremental_spend_usd": 0,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "aggregate_acceptance_requires_independent_reducer": True,
        "strict_timeout_semantics": (
            "BOUND_CAS_ACQUISITION_DEFINES_IRREVERSIBLE_START__"
            "INVALID_OR_MISSING_IDENTITY_CAN_NEVER_PRODUCE_SUCCESS_OR_RETRY__"
            "ANY_NON_SUCCESS_AFTER_CAS_COUNTS_FINAL_ZERO"
        ),
    }
    out = root / (safe_id + "__SLOT_RECEIPT_V7.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
