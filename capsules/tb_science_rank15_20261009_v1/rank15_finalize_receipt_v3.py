#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK15_V3"
SLOT = "terminal-bench-science/protein-active-learning::trial-0"
TASK = "terminal-bench-science/protein-active-learning"
DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    safe_id = os.environ.get("SAFE_ID") or "protein-active-learning-trial-0"
    base = root / "jobs" / safe_id
    guard = _read_json(root / "RANK15_PRESTART_GUARD.json")
    cas = _read_json(root / "RANK15_START_CAS_V3.json")

    cas_acquired = (
        cas.get("pass") is True
        and cas.get("acquired") is True
        and cas.get("task_started") is True
        and cas.get("slot_id") == SLOT
        and cas.get("task_digest") == DIGEST
    )
    task_started = cas_acquired

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
    errors: list[str] = []
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
    success = task_started and reward is not None and reward >= 1.0 and not errors

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
        "start_cas_acquired": cas_acquired,
        "start_cas_status": cas.get("status"),
        "start_cas_lock_ref": cas.get("lock_ref"),
        "start_cas_lock_commit_sha": cas.get("lock_commit_sha"),
        "prestart_guard_status": guard.get("status"),
        "prestart_guard_pass": guard.get("pass"),
        "prestart_input_tokens": guard.get("input_tokens"),
        "prestart_context_headroom_tokens": guard.get("context_headroom_tokens"),
        "prestart_instruction_sha256": guard.get("instruction_sha256"),
        "prestart_first_cycle_prompt_sha256": guard.get("first_cycle_prompt_sha256"),
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
        "strict_timeout_semantics": "CAS_ACQUIRED_DEFINES_IRREVERSIBLE_START__ANY_NON_SUCCESS_AFTER_CAS_COUNTS_FINAL_ZERO",
    }
    out = root / (safe_id + "__SLOT_RECEIPT_V3.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
