#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT_ID = "terminal-bench-science/protein-active-learning::trial-0"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
LLAMA_CPP_REV = "bec4772f6a2527d371557b5d2032641e5ff7619c"
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
HARBOR_VERSION = "0.23.0"
SERVER_CONTEXT_TOKENS = 16384
RESERVED_COMPLETION_TOKENS = 4096

CONTROL_BINDINGS = (
    "authority",
    "ledger",
    "epoch",
    "execution_claim",
    "behavior",
    "invariant_registry",
    "admission_guard",
    "preflight",
    "finalizer",
)
RUNTIME_BINDINGS = (
    "planner",
    "agent",
    "prestart_guard",
    "transport",
    "zero_exposure_tests",
    "all_cycle_proof",
    "start_cas",
    "generic_start_cas",
    "generic_ref_store",
    "finalizer",
    "preflight",
    "admission_guard",
    "execution_identity",
)


class ExecutionIdentityError(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExecutionIdentityError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def safe_path(root: Path, rel: str) -> Path:
    root = root.resolve()
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise ExecutionIdentityError("PATH_INVALID")
    path = (root / rel).resolve()
    if path == root or root not in path.parents:
        raise ExecutionIdentityError("PATH_ESCAPE:" + rel)
    if not path.is_file():
        raise ExecutionIdentityError("FILE_MISSING:" + rel)
    return path


def require_binding(
    root: Path,
    row: Any,
    label: str,
) -> tuple[Path, str]:
    if not isinstance(row, Mapping):
        raise ExecutionIdentityError("BINDING_MISSING:" + label)
    rel = row.get("path")
    expected = row.get("git_blob_sha")
    if not isinstance(rel, str) or not isinstance(expected, str):
        raise ExecutionIdentityError("BINDING_INVALID:" + label)
    path = safe_path(root, rel)
    actual = git_blob(path)
    if actual != expected:
        raise ExecutionIdentityError("BINDING_BLOB_MISMATCH:" + label)
    return path, actual


def build_execution_identity(
    root: Path,
    *,
    surface_rel: str = SURFACE_REL,
) -> dict[str, Any]:
    root = root.resolve()
    surface_path = safe_path(root, surface_rel)
    surface = read_json(surface_path)
    if surface.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1":
        raise ExecutionIdentityError("SURFACE_SCHEMA_INVALID")
    if surface.get("slot_id") != SLOT_ID or surface.get("task_digest") != TASK_DIGEST:
        raise ExecutionIdentityError("SURFACE_SLOT_OR_DIGEST_MISMATCH")

    workflow_rel = surface.get("workflow_path")
    workflow_expected = surface.get("workflow_git_blob_sha")
    if not isinstance(workflow_rel, str) or not isinstance(workflow_expected, str):
        raise ExecutionIdentityError("SURFACE_WORKFLOW_BINDING_INVALID")
    workflow_path = safe_path(root, workflow_rel)
    workflow_blob = git_blob(workflow_path)
    if workflow_blob != workflow_expected:
        raise ExecutionIdentityError("SURFACE_WORKFLOW_BLOB_MISMATCH")

    control_blobs: dict[str, str] = {}
    for label in CONTROL_BINDINGS:
        _path, blob = require_binding(root, surface.get(label), "surface." + label)
        control_blobs[label] = blob

    behavior_path, behavior_blob = require_binding(
        root, surface.get("behavior"), "surface.behavior"
    )
    behavior = read_json(behavior_path)
    runtime = behavior.get("runtime_bindings")
    if not isinstance(runtime, Mapping):
        raise ExecutionIdentityError("RUNTIME_BINDINGS_INVALID")

    runtime_blobs: dict[str, str] = {}
    for label in RUNTIME_BINDINGS:
        _path, blob = require_binding(root, runtime.get(label), "runtime." + label)
        runtime_blobs[label] = blob

    control_material = {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_CONTROL_IDENTITY_V1",
        "surface_git_blob_sha": git_blob(surface_path),
        "slot_id": SLOT_ID,
        "task_digest": TASK_DIGEST,
        "workflow_path": workflow_rel,
        "workflow_git_blob_sha": workflow_blob,
        "activation_path": surface.get("activation_path"),
        "control_bindings": control_blobs,
    }
    control_sha = canonical_sha256(control_material)

    runtime_material = {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_RUNTIME_IDENTITY_V2",
        "control_identity_sha256": control_sha,
        "behavior_git_blob_sha": behavior_blob,
        "runtime_bindings": runtime_blobs,
        "llama_cpp_commit": LLAMA_CPP_REV,
        "qwen_model_sha256": MODEL_SHA256,
        "harbor_version": HARBOR_VERSION,
        "server_context_tokens": SERVER_CONTEXT_TOKENS,
        "reserved_completion_tokens": RESERVED_COMPLETION_TOKENS,
    }
    return {
        "control_identity_sha256": control_sha,
        "control_identity_material": control_material,
        "runtime_identity_sha256": canonical_sha256(runtime_material),
        "runtime_identity_material": runtime_material,
        "surface": surface,
        "surface_git_blob_sha": control_material["surface_git_blob_sha"],
        "workflow_git_blob_sha": workflow_blob,
        "control_binding_blobs": control_blobs,
        "runtime_binding_blobs": runtime_blobs,
    }


def activation_blob(root: Path, surface: Mapping[str, Any]) -> str:
    rel = surface.get("activation_path")
    if not isinstance(rel, str) or not rel:
        raise ExecutionIdentityError("ACTIVATION_PATH_INVALID")
    return git_blob(safe_path(root, rel))


def validate_bound_start(
    root: Path,
    *,
    guard: Mapping[str, Any],
    cas: Mapping[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    identity = build_execution_identity(root)
    surface = identity["surface"]
    expected_prestart = sha256_file(root / "RANK15_PRESTART_GUARD.json")
    expected_activation = activation_blob(root, surface)
    checks = {
        "CONTROL_IDENTITY_MATCH": cas.get("control_identity_sha256") == identity["control_identity_sha256"],
        "RUNTIME_IDENTITY_MATCH": cas.get("runtime_identity_sha256") == identity["runtime_identity_sha256"],
        "WORKFLOW_BLOB_MATCH": cas.get("workflow_git_blob_sha") == identity["workflow_git_blob_sha"],
        "AUTHORITY_BLOB_MATCH": cas.get("authority_git_blob_sha") == identity["control_binding_blobs"]["authority"],
        "ACTIVATION_BLOB_MATCH": cas.get("activation_git_blob_sha") == expected_activation,
        "PRESTART_RECEIPT_SHA_MATCH": cas.get("prestart_receipt_sha256") == expected_prestart,
        "LOGICAL_ATTEMPT_ID_MATCH": (
            isinstance(guard.get("logical_attempt_id"), str)
            and cas.get("logical_attempt_id") == guard.get("logical_attempt_id")
        ),
        "REPLAY_AUTHORITY_FALSE": cas.get("replay_authority") is False,
        "REPLACEMENT_AUTHORITY_FALSE": cas.get("replacement_carrier_authority") is False,
    }
    errors = [
        "BOUND_START_IDENTITY_INVALID:" + label
        for label, passed in checks.items()
        if not passed
    ]
    return errors, identity
