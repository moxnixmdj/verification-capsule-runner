#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class BoundRuntimeError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BoundRuntimeError("BOUND_JSON_OBJECT_REQUIRED")
    return value


def _safe_repo_path(root: Path, rel: Any) -> Path:
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        raise BoundRuntimeError("BOUND_PATH_INVALID")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise BoundRuntimeError("BOUND_PATH_ESCAPES_REPOSITORY")
    resolved = (root / p).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise BoundRuntimeError("BOUND_PATH_ESCAPES_REPOSITORY") from exc
    if not resolved.is_file():
        raise BoundRuntimeError("BOUND_FILE_MISSING")
    return resolved


def _require_binding(root: Path, row: Any, label: str) -> tuple[Path, str]:
    if not isinstance(row, dict):
        raise BoundRuntimeError(label + "_BINDING_REQUIRED")
    path = _safe_repo_path(root, row.get("path"))
    expected = row.get("git_blob_sha")
    if not isinstance(expected, str) or len(expected) != 40:
        raise BoundRuntimeError(label + "_BLOB_INVALID")
    actual = git_blob_sha(path)
    if actual != expected:
        raise BoundRuntimeError(label + "_BLOB_MISMATCH")
    return path, actual


def resolve_runtime_binding(
    *,
    root: Path,
    surface_rel: str,
    runtime_key: str,
) -> Path:
    surface_path = _safe_repo_path(root, surface_rel)
    surface = _read_json(surface_path)
    behavior_path, _ = _require_binding(root, surface.get("behavior"), "SURFACE_BEHAVIOR")
    behavior = _read_json(behavior_path)
    bindings = behavior.get("runtime_bindings")
    if not isinstance(bindings, dict):
        raise BoundRuntimeError("BEHAVIOR_RUNTIME_BINDINGS_REQUIRED")
    runtime_path, _ = _require_binding(root, bindings.get(runtime_key), "RUNTIME_" + runtime_key.upper())
    return runtime_path
