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
WORKFLOW = ".github/workflows/execute-tb-science-rank15-20261009-v3.yml"
SURFACE = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
INVARIANTS = "execution_guard/CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1.json"
ADMISSION = "execution_guard/terminal_execution_admission_v2.py"
BEHAVIOR = "execution_guard/TB_SCIENCE_RANK15_EXECUTION_BEHAVIOR_V3.json"
CAS = "execution_guard/terminal_slot_start_cas_v1.py"
PLANNER = "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_science_planner_v3.py"
AGENT = "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_science_agent_v3.py"
PRESTART = "capsules/tb_science_rank15_20261009_v1/rank15_prestart_token_guard_v3.py"
TRANSPORT = "capsules/tb_science_rank15_20261009_v1/canonical/runtime/harbor_environment_transport.py"


def _load(path: Path) -> dict[str, Any]:
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


def _scored_results(root: Path, base: Path):
    results = []
    for path in base.rglob("result.json") if base.exists() else []:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict):
            results.append((path, obj))

    scored = []
    exceptions = []
    for path, obj in results:
        verifier = obj.get("verifier_result")
        if isinstance(verifier, dict) and isinstance(verifier.get("rewards"), dict):
            scored.append((path, obj))
        exc = obj.get("exception_info")
        if isinstance(exc, dict):
            exceptions.append(
                {
                    "path": str(path.relative_to(root)),
                    "exception_type": exc.get("exception_type"),
                    "exception_message": exc.get("exception_message"),
                }
            )
    return results, scored, exceptions


def build_receipt(root: Path, env: dict[str, str]) -> dict[str, Any]:
    root = root.resolve()
    safe_id = env.get("SAFE_ID") or "protein-active-learning-trial-0"
    base = root / "jobs" / safe_id
    guard = _load(root / "RANK15_PRESTART_GUARD.json")
    cas_receipt = _load(root / "TERMINAL_SLOT_START_CAS_RECEIPT.json")
    start_intent = _load(root / "RANK15_START_INTENT.json")
    surface = _load(root / SURFACE)

    results, scored, exception_info = _scored_results(root, base)
    reward = None
    errors: list[str] = []
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

    harbor_outcome = env.get("HARBOR_OUTCOME") or "skipped"
    carrier_ready = env.get("CARRIER_READY") == "true"
    task_started = harbor_outcome in {"success", "failure"}
    cas_committed = cas_receipt.get("status") == "TASK_START_INTENT_COMMITTED"

    if task_started and not cas_committed:
        errors.append("TASK_STARTED_WITHOUT_DURABLE_START_CAS")
    if task_started:
        if surface.get("workflow_path") != WORKFLOW:
            errors.append("STARTED_ON_NONCURRENT_WORKFLOW_SURFACE")
        if surface.get("slot_id") != SLOT or surface.get("task_digest") != DIGEST:
            errors.append("STARTED_ON_WRONG_CURRENT_SLOT")
        if surface.get("execution_authority") is not True:
            errors.append("STARTED_WITHOUT_ACTIVE_EXECUTION_AUTHORITY")

    success = (
        task_started
        and cas_committed
        and reward is not None
        and reward >= 1.0
        and not errors
    )

    if not task_started:
        if not carrier_ready:
            errors = ["TASK_NOT_STARTED__PREEXPOSURE_ABORT__CARRIER_NOT_QUALIFIED"]
        elif guard.get("pass") is not True:
            errors = ["TASK_NOT_STARTED__PREEXPOSURE_ABORT__TOKEN_OR_GUARD"]
        elif not cas_committed:
            errors = ["TASK_NOT_STARTED__PREEXPOSURE_ABORT__START_CAS_NOT_COMMITTED"]
        else:
            errors = ["TASK_NOT_STARTED__POST_CAS_START_OUTCOME_UNCERTAIN__NO_REPLAY_AUTHORITY"]

    result_hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path, _ in results
    }
    status = (
        "PREEXPOSURE_ABORT_NONCONSUMING"
        if not task_started and not cas_committed
        else (
            "START_OUTCOME_UNCERTAIN__NO_REPLAY"
            if not task_started and cas_committed
            else ("SUCCESS" if success else "FINAL_ZERO")
        )
    )

    bindings = {}
    for label, rel in {
        "workflow": WORKFLOW,
        "current_surface": SURFACE,
        "invariant_registry": INVARIANTS,
        "admission_guard": ADMISSION,
        "behavior": BEHAVIOR,
        "start_cas": CAS,
        "planner": PLANNER,
        "agent": AGENT,
        "prestart_guard": PRESTART,
        "transport": TRANSPORT,
    }.items():
        bindings[label] = {"path": rel, "git_blob_sha": _git_blob(root / rel)}

    receipt = {
        "schema": SCHEMA,
        "slot_id": SLOT,
        "task_name": TASK,
        "task_digest": DIGEST,
        "status": status,
        "reward": None if not task_started else (reward if reward is not None else 0.0),
        "slot_success_evidence": bool(success),
        "carrier_ready": carrier_ready,
        "task_read": bool(guard.get("task_read")),
        "task_started": task_started,
        "prestart_guard_status": guard.get("status"),
        "prestart_guard_pass": guard.get("pass"),
        "prestart_input_tokens": guard.get("input_tokens"),
        "prestart_context_headroom_tokens": guard.get("context_headroom_tokens"),
        "prestart_instruction_sha256": guard.get("instruction_sha256"),
        "prestart_first_cycle_prompt_sha256": guard.get("first_cycle_prompt_sha256"),
        "prestart_logical_attempt_id": guard.get("logical_attempt_id"),
        "prestart_payload_sha256": guard.get("payload_sha256"),
        "raw_task_obligation_count": guard.get("raw_task_obligation_count"),
        "task_start_intent_committed": cas_committed,
        "start_intent_sha256": _sha256(root / "RANK15_START_INTENT.json"),
        "start_cas_receipt_sha256": _sha256(root / "TERMINAL_SLOT_START_CAS_RECEIPT.json"),
        "start_cas_key": cas_receipt.get("key"),
        "start_cas_replay_authority": cas_receipt.get("replay_authority", False),
        "start_cas_replacement_carrier_authority": cas_receipt.get("replacement_carrier_authority", False),
        "start_intent": start_intent,
        "errors": errors,
        "exception_info": exception_info,
        "harbor_step_outcome": harbor_outcome,
        "bindings": bindings,
        "qwen_model_sha256": "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
        "llama_cpp_commit": "bec4772f6a2527d371557b5d2032641e5ff7619c",
        "server_context_tokens": 16384,
        "reserved_completion_tokens": 4096,
        "strict_timeout_semantics": "SUCCESS_REQUIRES_POSITIVE_VERIFIER_EVIDENCE_AND_DURABLE_START_CAS__ANY_FINAL_NON_SUCCESS_AFTER_START_COUNTS_ZERO",
        "github_run_id": env.get("GITHUB_RUN_ID"),
        "github_run_attempt": env.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": env.get("GITHUB_SHA"),
        "result_hashes": result_hashes,
        "execution_authority_consumed": task_started,
        "benchmark_trials_consumed": 1 if task_started else 0,
        "rerun_credit": False,
        "replacement_carrier_authority": False,
        "incremental_spend_usd": 0,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "aggregate_target_rule": "ONE_SLOT_SUCCESS_IS_EVIDENCE_ONLY__TB_SCIENCE_GE_58_7_REQUIRES_AGGREGATE_LEDGER_REDUCER",
    }
    return receipt


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    env = {str(k): str(v) for k, v in os.environ.items()}
    receipt = build_receipt(root, env)
    safe_id = env.get("SAFE_ID") or "protein-active-learning-trial-0"
    out = root / (safe_id + "__SLOT_RECEIPT_V3.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
