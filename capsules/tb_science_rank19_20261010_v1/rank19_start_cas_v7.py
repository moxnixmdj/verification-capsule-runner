#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXECUTION_GUARD = ROOT / "execution_guard"
if str(EXECUTION_GUARD) not in sys.path:
    sys.path.insert(0, str(EXECUTION_GUARD))

import terminal_slot_start_cas_v2 as generic_cas
import rank19_logical_attempt_binding_v1 as attempt_binding

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK19_START_CAS_V7"
SLOT_ID = "terminal-bench-science/diag-chipseq::trial-0"
TASK_DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
EXPECTED_REPOSITORY = "moxnixmdj/verification-capsule-runner"
EXPECTED_BASE = "terminal-execution-v1"
EXPECTED_HEAD = "execute/tb-science-rank19-20261010-v1"
ACTIVATION_REL = "capsules/tb_science_rank19_20261010_v1/ACTIVATE_RANK19_V1_PR.json"
SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
PREFLIGHT_RECEIPT = "RANK19_PRESTART_GUARD.json"
AGENT_READY_REL = "RANK19_AGENT_START_BARRIER/AGENT_READY.json"
CHECK_RECEIPT = "RANK19_START_CAS_CHECK_V6.json"
ACQUIRE_RECEIPT = "RANK19_START_CAS_V6.json"
LLAMA_CPP_REV = "bec4772f6a2527d371557b5d2032641e5ff7619c"
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
HARBOR_VERSION = "0.23.0"
SERVER_CONTEXT_TOKENS = 16384
RESERVED_COMPLETION_TOKENS = 4096
STATUS_STORE_ANCHOR_SHA = "8545e23a3113b2e4aef753799eb71d7c192ae815"


class StartCASError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StartCASError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _write_output(name: str, value: str) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _safe_repo_path(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise StartCASError("BOUND_PATH_INVALID")
    path = (root / rel).resolve()
    if path == root or root not in path.parents:
        raise StartCASError("BOUND_PATH_ESCAPE:" + rel)
    if not path.is_file():
        raise StartCASError("BOUND_FILE_MISSING:" + rel)
    return path


def _event_context(root: Path) -> dict[str, Any]:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise StartCASError("PULL_REQUEST_EVENT_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise StartCASError("FIRST_RUN_ATTEMPT_REQUIRED")
    if os.environ.get("GITHUB_BASE_REF") != EXPECTED_BASE:
        raise StartCASError("BASE_REF_MISMATCH")
    if os.environ.get("GITHUB_HEAD_REF") != EXPECTED_HEAD:
        raise StartCASError("HEAD_REF_MISMATCH")
    if os.environ.get("GITHUB_REPOSITORY") != EXPECTED_REPOSITORY:
        raise StartCASError("REPOSITORY_MISMATCH")
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH") or "")
    if not event_path.is_file():
        raise StartCASError("GITHUB_EVENT_PATH_REQUIRED")
    event = _read_json(event_path)
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise StartCASError("PULL_REQUEST_OBJECT_REQUIRED")
    head = pr.get("head")
    base = pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise StartCASError("PULL_REQUEST_REFS_REQUIRED")
    head_repo = head.get("repo")
    if not isinstance(head_repo, dict) or head_repo.get("full_name") != EXPECTED_REPOSITORY:
        raise StartCASError("SAME_REPOSITORY_HEAD_REQUIRED")
    if head.get("ref") != EXPECTED_HEAD or base.get("ref") != EXPECTED_BASE:
        raise StartCASError("EVENT_REF_MISMATCH")

    activation_path = root / ACTIVATION_REL
    activation = _read_json(activation_path)
    if activation.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK19_ACTIVATION_V7":
        raise StartCASError("ACTIVATION_SCHEMA_INVALID")
    if activation.get("activate") is not True:
        raise StartCASError("ACTIVATION_NOT_ARMED")
    if activation.get("slot_id") != SLOT_ID or activation.get("task_digest") != TASK_DIGEST:
        raise StartCASError("ACTIVATION_SLOT_OR_DIGEST_MISMATCH")

    surface_path = root / SURFACE_REL
    surface = _read_json(surface_path)
    if surface.get("execution_authority") is not True:
        raise StartCASError("EXECUTION_AUTHORITY_NOT_ACTIVE")
    if surface.get("task_started") is not False:
        raise StartCASError("SURFACE_TASK_ALREADY_STARTED")
    if surface.get("slot_id") != SLOT_ID or surface.get("task_digest") != TASK_DIGEST:
        raise StartCASError("SURFACE_SLOT_OR_DIGEST_MISMATCH")

    epoch_path, epoch_blob = _require_binding(root, surface.get("epoch"), "surface.epoch")
    claim_path, claim_blob = _require_binding(
        root, surface.get("execution_claim"), "surface.execution_claim"
    )
    epoch = _read_json(epoch_path)
    claim = _read_json(claim_path)
    if epoch.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK19_EPOCH_V7":
        raise StartCASError("EPOCH_SCHEMA_INVALID")
    if claim.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK19_EXECUTION_CLAIM_V7":
        raise StartCASError("EXECUTION_CLAIM_SCHEMA_INVALID")
    for label, doc in (("epoch", epoch), ("claim", claim)):
        if doc.get("slot_id") != SLOT_ID or doc.get("task_digest") != TASK_DIGEST:
            raise StartCASError(label.upper() + "_SLOT_OR_DIGEST_MISMATCH")
    if epoch.get("execution_branch") != EXPECTED_HEAD or claim.get("execution_branch") != EXPECTED_HEAD:
        raise StartCASError("EPOCH_OR_CLAIM_HEAD_REF_MISMATCH")
    if claim.get("epoch_git_blob_sha") != epoch_blob:
        raise StartCASError("EXECUTION_CLAIM_EPOCH_BINDING_MISMATCH")
    if claim.get("activation_filename") != "ACTIVATE_RANK19_V1_PR.json":
        raise StartCASError("EXECUTION_CLAIM_ACTIVATION_MISMATCH")

    return {
        "event": event,
        "activation": activation,
        "activation_path": activation_path,
        "surface": surface,
        "surface_path": surface_path,
        "epoch": epoch,
        "epoch_path": epoch_path,
        "epoch_git_blob_sha": epoch_blob,
        "execution_claim": claim,
        "execution_claim_path": claim_path,
        "execution_claim_git_blob_sha": claim_blob,
    }


def _open_stores():
    """Open new status store plus read-only legacy ref store for migration guard."""
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if repo != EXPECTED_REPOSITORY:
        raise StartCASError("GITHUB_REPOSITORY_MISMATCH")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        raise StartCASError("GITHUB_TOKEN_REQUIRED")
    github_sha = os.environ.get("GITHUB_SHA") or ""
    if not re.fullmatch(r"[0-9a-f]{40}", github_sha):
        raise StartCASError("GITHUB_SHA_INVALID")

    req = generic_cas.request_factory(token)
    status, commit, _headers = req("GET", f"/repos/{repo}/git/commits/{github_sha}")
    tree = (commit.get("tree") or {}).get("sha") if status == 200 and isinstance(commit, dict) else None
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise StartCASError("BASE_TREE_UNCONFIRMED__NO_START")

    # The execution record still binds the actual PR merge SHA, but the
    # durable start object itself must live at one repository-wide coordinate.
    # Otherwise two PR merge commits can each create the same logical slot key
    # without seeing one another, which Rank18 proved is unsafe.
    anchor_status, _anchor_commit, _headers = req(
        "GET", f"/repos/{repo}/git/commits/{STATUS_STORE_ANCHOR_SHA}"
    )
    if anchor_status != 200:
        raise StartCASError("STATUS_STORE_ANCHOR_UNCONFIRMED__NO_START")

    status_store = generic_cas.SerializedStatusObjectStore(
        req, repo, STATUS_STORE_ANCHOR_SHA, generic_cas.NAMESPACE
    )
    # V4 wrote into this legacy ref namespace. Reads remain required during
    # migration so a historical start can never disappear merely because the
    # writable backend changed.
    legacy_ref_store = generic_cas.v1.GitHubRefStore(
        req, repo, github_sha, tree, generic_cas.NAMESPACE
    )
    return status_store, legacy_ref_store


def _key() -> str:
    return generic_cas.slot_start_key(SLOT_ID, TASK_DIGEST)


def _read_start_record(store) -> dict[str, Any] | None:
    try:
        record = store.read(_key())
    except Exception as exc:
        raise StartCASError("START_RECORD_READ_UNCONFIRMED__NO_START") from exc
    if record is not None and not isinstance(record, dict):
        raise StartCASError("START_RECORD_INVALID")
    return record


def _require_binding(root: Path, row: Any, label: str) -> tuple[Path, str]:
    if not isinstance(row, dict):
        raise StartCASError("BINDING_MISSING:" + label)
    rel = row.get("path")
    expected = row.get("git_blob_sha")
    if not isinstance(rel, str) or not isinstance(expected, str):
        raise StartCASError("BINDING_INVALID:" + label)
    path = _safe_repo_path(root, rel)
    actual = _git_blob(path)
    if actual != expected:
        raise StartCASError("BINDING_BLOB_MISMATCH:" + label)
    return path, actual


def _runtime_identity(root: Path, surface: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    behavior_path, behavior_blob = _require_binding(
        root, surface.get("behavior"), "surface.behavior"
    )
    behavior = _read_json(behavior_path)
    bindings = behavior.get("runtime_bindings")
    if not isinstance(bindings, dict):
        raise StartCASError("RUNTIME_BINDINGS_INVALID")

    exact_bindings: dict[str, str] = {}
    for label in (
        "planner",
        "agent",
        "prestart_guard",
        "transport",
        "zero_exposure_tests",
        "all_cycle_proof",
        "start_cas",
        "generic_start_cas",
        "identity_primitive",
        "start_barrier",
        "generic_status_store",
        "generic_ref_store",
        "causal_journal",
        "causal_journal_bridge",
        "status_journal_runner",
        "finalizer",
        "preflight",
        "admission_guard",
    ):
        _path, blob = _require_binding(root, bindings.get(label), "runtime." + label)
        exact_bindings[label] = blob

    epoch_path, epoch_blob = _require_binding(
        root, surface.get("epoch"), "surface.epoch"
    )
    claim_path, claim_blob = _require_binding(
        root, surface.get("execution_claim"), "surface.execution_claim"
    )
    del epoch_path, claim_path

    material = {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK19_RUNTIME_IDENTITY_V7",
        "behavior_git_blob_sha": behavior_blob,
        "epoch_git_blob_sha": epoch_blob,
        "execution_claim_git_blob_sha": claim_blob,
        "runtime_bindings": exact_bindings,
        "llama_cpp_commit": LLAMA_CPP_REV,
        "qwen_model_sha256": MODEL_SHA256,
        "harbor_version": HARBOR_VERSION,
        "server_context_tokens": SERVER_CONTEXT_TOKENS,
        "reserved_completion_tokens": RESERVED_COMPLETION_TOKENS,
    }
    return _canonical_sha256(material), material


def _build_start_intent(root: Path, context: dict[str, Any]) -> tuple[generic_cas.StartIntent, dict[str, Any]]:
    guard_path = root / PREFLIGHT_RECEIPT
    guard = _read_json(guard_path)
    if (
        guard.get("pass") is not True
        or guard.get("task_read") is not True
        or guard.get("task_started") is not False
        or guard.get("task_digest") != TASK_DIGEST
        or not str(guard.get("status") or "").startswith("PASS__RANK19_V1_V13_")
    ):
        raise StartCASError("PRESTART_GUARD_NOT_AUTHORIZED")

    logical_attempt_id = guard.get("logical_attempt_id")
    if not isinstance(logical_attempt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", logical_attempt_id):
        raise StartCASError("PRESTART_LOGICAL_ATTEMPT_ID_INVALID")
    expected_logical_attempt_id = attempt_binding.logical_attempt_id()
    if logical_attempt_id != expected_logical_attempt_id:
        raise StartCASError("PRESTART_LOGICAL_ATTEMPT_ID_NOT_CLAIM_BOUND")

    ready_path = root / AGENT_READY_REL
    if not ready_path.is_file():
        raise StartCASError("AGENT_READY_RECEIPT_MISSING")
    ready = _read_json(ready_path)
    if ready.get("schema") != "PROJECT_BRAIN_AGENT_START_READY_V1":
        raise StartCASError("AGENT_READY_SCHEMA_INVALID")
    if ready.get("slot_id") != SLOT_ID or ready.get("task_digest") != TASK_DIGEST:
        raise StartCASError("AGENT_READY_SLOT_OR_DIGEST_MISMATCH")
    if guard.get("execution_claim_binding_digest") != attempt_binding.execution_claim_binding_digest():\n        raise StartCASError("PRESTART_EXECUTION_CLAIM_BINDING_DIGEST_MISMATCH")\n    if ready.get("logical_attempt_id") != logical_attempt_id:
        raise StartCASError("AGENT_READY_LOGICAL_ATTEMPT_MISMATCH")
    if ready.get("task_started") is not False or ready.get("benchmark_trials_consumed") != 0:
        raise StartCASError("AGENT_READY_PRESTART_ACCOUNTING_INVALID")
    agent_ready_sha256 = _sha256_file(ready_path)

    surface = context["surface"]
    workflow_rel = surface.get("workflow_path")
    workflow_expected = surface.get("workflow_git_blob_sha")
    if not isinstance(workflow_rel, str) or not isinstance(workflow_expected, str):
        raise StartCASError("SURFACE_WORKFLOW_BINDING_INVALID")
    workflow_path = _safe_repo_path(root, workflow_rel)
    workflow_blob = _git_blob(workflow_path)
    if workflow_blob != workflow_expected:
        raise StartCASError("SURFACE_WORKFLOW_BLOB_MISMATCH")

    authority_path, authority_blob = _require_binding(
        root, surface.get("authority"), "surface.authority"
    )
    del authority_path
    activation_path = context["activation_path"]
    activation_blob = _git_blob(activation_path)

    runtime_identity, runtime_material = _runtime_identity(root, surface)
    prestart_sha256 = _sha256_file(guard_path)
    github_run_id = os.environ.get("GITHUB_RUN_ID") or ""
    github_sha = os.environ.get("GITHUB_SHA") or ""

    intent = generic_cas.StartIntent(
        slot_id=SLOT_ID,
        task_digest=TASK_DIGEST,
        logical_attempt_id=logical_attempt_id,
        workflow_git_blob_sha=workflow_blob,
        authority_git_blob_sha=authority_blob,
        activation_git_blob_sha=activation_blob,
        runtime_identity_sha256=runtime_identity,
        prestart_receipt_sha256=prestart_sha256,
        agent_ready_receipt_sha256=agent_ready_sha256,
        github_run_id=github_run_id,
        github_sha=github_sha,
    )
    intent.validate()
    return intent, {
        "logical_attempt_id": logical_attempt_id,
        "workflow_git_blob_sha": workflow_blob,
        "authority_git_blob_sha": authority_blob,
        "activation_git_blob_sha": activation_blob,
        "runtime_identity_sha256": runtime_identity,
        "runtime_identity_material": runtime_material,
        "prestart_receipt_sha256": prestart_sha256,
        "agent_ready_receipt_sha256": agent_ready_sha256,
        "prestart_payload_sha256": guard.get("payload_sha256"),
        "prestart_request_identity_sha256": guard.get("request_identity_sha256"),
    }


def _result(mode: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": mode,
        "slot_id": SLOT_ID,
        "task_digest": TASK_DIGEST,
        "generic_cas_schema": generic_cas.SCHEMA,
        "generic_cas_namespace": generic_cas.NAMESPACE,
        "generic_cas_key": _key(),
        "durable_backend": "GITHUB_COMMIT_STATUS_OBJECT_STORE_V1_SLOT_GLOBAL_ANCHOR",
        "status_store_anchor_sha": STATUS_STORE_ANCHOR_SHA,
        "status_store_execution_sha_scoped": False,
        "legacy_ref_migration_guard_required": True,
        "legacy_ref_absent": False,
        "pass": False,
        "lock_absent": False,
        "acquired": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-absent", action="store_true")
    group.add_argument("--acquire", action="store_true")
    args = parser.parse_args()

    mode = "check-absent" if args.check_absent else "acquire"
    result = _result(mode)
    root = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    output = root / (CHECK_RECEIPT if args.check_absent else ACQUIRE_RECEIPT)
    rc = 1
    try:
        context = _event_context(root)
        store, legacy_store = _open_stores()

        legacy_existing = _read_start_record(legacy_store)
        legacy_absent = legacy_existing is None
        result["legacy_ref_absent"] = legacy_absent
        if legacy_existing is not None:
            result["legacy_existing_record_run_id"] = legacy_existing.get("github_run_id")
            result["legacy_existing_record_logical_attempt_id"] = legacy_existing.get("logical_attempt_id")

        existing = _read_start_record(store)
        status_absent = existing is None
        absent = legacy_absent and status_absent
        result["lock_absent"] = absent
        result["status_record_absent"] = status_absent
        if existing is not None:
            result["existing_record_run_id"] = existing.get("github_run_id")
            result["existing_record_logical_attempt_id"] = existing.get("logical_attempt_id")

        if args.check_absent:
            result["pass"] = absent
            result["status"] = (
                "PASS__LEGACY_REF_AND_STATUS_START_RECORD_ABSENT__NO_TASK_START"
                if absent
                else "FAIL_CLOSED__START_RECORD_ALREADY_EXISTS"
            )
            rc = 0 if absent else 1
        elif not legacy_absent:
            result["status"] = "FAIL_CLOSED__LEGACY_REF_START_ALREADY_EXISTS"
        elif not status_absent:
            result["status"] = "FAIL_CLOSED__STATUS_START_ALREADY_EXISTS"
        else:
            intent, binding = _build_start_intent(root, context)
            receipt = generic_cas.reserve_start_once(store, intent)
            persisted = _read_start_record(store)
            expected = {
                "slot_id": intent.slot_id,
                "task_digest": intent.task_digest,
                "logical_attempt_id": intent.logical_attempt_id,
                "workflow_git_blob_sha": intent.workflow_git_blob_sha,
                "authority_git_blob_sha": intent.authority_git_blob_sha,
                "activation_git_blob_sha": intent.activation_git_blob_sha,
                "runtime_identity_sha256": intent.runtime_identity_sha256,
                "prestart_receipt_sha256": intent.prestart_receipt_sha256,
                "agent_ready_receipt_sha256": intent.agent_ready_receipt_sha256,
                "github_run_id": intent.github_run_id,
                "github_sha": intent.github_sha,
                "replay_authority": False,
                "replacement_carrier_authority": False,
            }
            if not isinstance(persisted, dict):
                raise StartCASError("START_RECORD_POSTWRITE_READ_MISSING")
            for key, expected_value in expected.items():
                if persisted.get(key) != expected_value:
                    raise StartCASError("START_RECORD_POSTWRITE_BINDING_MISMATCH:" + key)

            result.update(binding)
            result.update({
                "pass": True,
                "acquired": True,
                "task_started": True,
                "benchmark_trials_consumed": 1,
                "status": "PASS__AGENT_READY_BOUND_START_COMMITTED__IRREVERSIBLE_SLOT_START",
                "generic_cas_receipt": receipt,
                "durable_record_sha256": _canonical_sha256(persisted),
            })
            rc = 0
    except Exception as exc:
        result["status"] = "FAIL_CLOSED__START_CAS_ERROR"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)

    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_output("lock_absent", "true" if result.get("lock_absent") else "false")
    _write_output("acquired", "true" if result.get("acquired") else "false")
    _write_output("receipt", str(output))
    print(json.dumps(result, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
