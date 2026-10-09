#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "capsules/tb_science_rank15_20261009_v1"
SURFACE = ROOT / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT = "terminal-bench-science/protein-active-learning::trial-0"
DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
WORKFLOW = ".github/workflows/execute-tb-science-rank15-20261009-v3.yml"
ACTIVATION = "capsules/tb_science_rank15_20261009_v1/ACTIVATE_RANK15_V3_PR.json"
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V3"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def safe(rel: str) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise RuntimeError("PATH_INVALID")
    path = (ROOT / rel).resolve()
    if path == ROOT or ROOT not in path.parents:
        raise RuntimeError("PATH_ESCAPE:" + rel)
    return path


def require_binding(row: Any, errors: list[str], label: str) -> None:
    if not isinstance(row, Mapping):
        errors.append("BINDING_MISSING:" + label)
        return
    rel, sha = row.get("path"), row.get("git_blob_sha")
    if not isinstance(rel, str) or not isinstance(sha, str):
        errors.append("BINDING_INVALID:" + label)
        return
    path = safe(rel)
    if not path.is_file():
        errors.append("BINDING_FILE_MISSING:" + label)
    elif git_blob(path) != sha:
        errors.append("BINDING_BLOB_MISMATCH:" + label)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-activation", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    try:
        surface = read_json(SURFACE)
        if surface.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1":
            errors.append("SURFACE_SCHEMA_INVALID")
        if surface.get("execution_authority") is not True:
            errors.append("EXECUTION_AUTHORITY_NOT_ACTIVE")
        if surface.get("task_read_authority") is not True:
            errors.append("TASK_READ_AUTHORITY_NOT_ACTIVE")
        if surface.get("task_started") is not False:
            errors.append("TASK_ALREADY_STARTED")
        if surface.get("benchmark_trials_consumed") != 0:
            errors.append("RANK15_TRIAL_ALREADY_CONSUMED")
        if surface.get("slot_id") != SLOT or surface.get("task_digest") != DIGEST:
            errors.append("SURFACE_SLOT_OR_DIGEST_MISMATCH")
        if surface.get("workflow_path") != WORKFLOW:
            errors.append("SURFACE_WORKFLOW_PATH_MISMATCH")
        workflow_path = safe(WORKFLOW)
        if git_blob(workflow_path) != surface.get("workflow_git_blob_sha"):
            errors.append("SURFACE_WORKFLOW_BLOB_MISMATCH")

        for key in ("behavior", "authority", "ledger", "invariant_registry", "admission_guard"):
            require_binding(surface.get(key), errors, "surface." + key)

        behavior_row = surface.get("behavior")
        behavior = read_json(safe(behavior_row["path"])) if isinstance(behavior_row, Mapping) else {}
        if behavior.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_BEHAVIOR_V3":
            errors.append("BEHAVIOR_SCHEMA_INVALID")
        if behavior.get("slot_id") != SLOT or behavior.get("task_digest") != DIGEST:
            errors.append("BEHAVIOR_SLOT_OR_DIGEST_MISMATCH")
        if behavior.get("workflow_path") != WORKFLOW:
            errors.append("BEHAVIOR_WORKFLOW_MISMATCH")
        facts = behavior.get("behavior")
        if not isinstance(facts, Mapping):
            errors.append("BEHAVIOR_FACTS_INVALID")
        else:
            for key in (
                "all_cycle_context_fit_by_construction",
                "durable_start_cas_required",
                "task_start_defined_by_cas_acquisition",
                "aggregate_acceptance_credit_from_single_slot_forbidden",
            ):
                if facts.get(key) is not True:
                    errors.append("BEHAVIOR_FACT_REQUIRED:" + key)

        bindings = behavior.get("runtime_bindings")
        if not isinstance(bindings, Mapping):
            errors.append("RUNTIME_BINDINGS_INVALID")
        else:
            for key in (
                "planner", "agent", "prestart_guard", "transport", "zero_exposure_tests",
                "start_cas", "finalizer", "preflight", "all_cycle_proof",
            ):
                require_binding(bindings.get(key), errors, "runtime." + key)

        proof_row = bindings.get("all_cycle_proof") if isinstance(bindings, Mapping) else None
        if isinstance(proof_row, Mapping):
            proof = read_json(safe(proof_row["path"]))
            if proof.get("status") != "PASS__STATIC_ADVERSARIAL_AND_EXACT_PINNED_GGUF_TOKENIZER_PROOF__ALL_CYCLE_CONTEXT_ENVELOPE_BY_CONSTRUCTION__ZERO_EXPOSURE":
                errors.append("ALL_CYCLE_PROOF_STATUS_INVALID")
            theorem = proof.get("theorem")
            if not isinstance(theorem, Mapping) or theorem.get("conclusion") != "IF_THE_EXACT_RESERVED_CYCLE0_PAYLOAD_PASSES_PRESTART_THEN_EVERY_REACHABLE_LATER_PLANNER_WIRE_PAYLOAD_IS_CONTEXT_ADMISSIBLE_BY_CONSTRUCTION":
                errors.append("ALL_CYCLE_THEOREM_INVALID")

        if args.require_activation:
            activation_path = safe(ACTIVATION)
            if not activation_path.is_file():
                errors.append("ACTIVATION_FILE_MISSING")
            else:
                activation = read_json(activation_path)
                if activation.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V3":
                    errors.append("ACTIVATION_SCHEMA_INVALID")
                if activation.get("activate") is not True:
                    errors.append("ACTIVATION_NOT_ARMED")
                if activation.get("slot_id") != SLOT or activation.get("task_digest") != DIGEST:
                    errors.append("ACTIVATION_SLOT_OR_DIGEST_MISMATCH")

            if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
                errors.append("PULL_REQUEST_EVENT_REQUIRED")
            if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
                errors.append("FIRST_RUN_ATTEMPT_REQUIRED")
            if os.environ.get("GITHUB_BASE_REF") != "terminal-execution-v1":
                errors.append("BASE_REF_MISMATCH")
            if os.environ.get("GITHUB_HEAD_REF") != "execute/tb-science-rank15-20261009-v3":
                errors.append("HEAD_REF_MISMATCH")
            event_path = Path(os.environ.get("GITHUB_EVENT_PATH") or "")
            if not event_path.is_file():
                errors.append("EVENT_FILE_MISSING")
            else:
                event = read_json(event_path)
                pr = event.get("pull_request")
                head = pr.get("head") if isinstance(pr, Mapping) else None
                head_repo = head.get("repo") if isinstance(head, Mapping) else None
                if not isinstance(head_repo, Mapping) or head_repo.get("full_name") != os.environ.get("GITHUB_REPOSITORY"):
                    errors.append("SAME_REPOSITORY_HEAD_REQUIRED")
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))

    result = {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    (ROOT / "RANK15_EXECUTION_PREFLIGHT_V3.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
