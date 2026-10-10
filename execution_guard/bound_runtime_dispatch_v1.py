#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"


class BoundRuntimeDispatchError(RuntimeError):
    pass


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BoundRuntimeDispatchError("JSON_INVALID:" + str(path)) from exc
    if not isinstance(value, dict):
        raise BoundRuntimeDispatchError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _safe_bound_file(root: Path, ref: Any, label: str) -> tuple[Path, str]:
    if not isinstance(ref, Mapping):
        raise BoundRuntimeDispatchError("BINDING_MISSING:" + label)
    rel = ref.get("path")
    expected = ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise BoundRuntimeDispatchError("BOUND_PATH_INVALID:" + label)
    if not isinstance(expected, str) or len(expected) != 40:
        raise BoundRuntimeDispatchError("BOUND_BLOB_INVALID:" + label)
    root = root.resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise BoundRuntimeDispatchError("BOUND_PATH_ESCAPE:" + label) from exc
    if not path.is_file() or path.is_symlink():
        raise BoundRuntimeDispatchError("BOUND_FILE_INVALID:" + label)
    actual = _git_blob(path)
    if actual != expected:
        raise BoundRuntimeDispatchError("BOUND_BLOB_MISMATCH:" + label)
    return path, actual


def resolve_bound_runtime(
    *,
    root: str | Path,
    runtime_key: str,
    surface_rel: str = DEFAULT_SURFACE_REL,
) -> dict[str, str]:
    root_path = Path(root).resolve()
    if not runtime_key or not isinstance(runtime_key, str):
        raise BoundRuntimeDispatchError("RUNTIME_KEY_REQUIRED")
    surface_path = (root_path / surface_rel).resolve()
    try:
        surface_path.relative_to(root_path)
    except ValueError as exc:
        raise BoundRuntimeDispatchError("SURFACE_PATH_ESCAPE") from exc
    if not surface_path.is_file() or surface_path.is_symlink():
        raise BoundRuntimeDispatchError("SURFACE_FILE_INVALID")
    surface = _read_json(surface_path)

    behavior_path, behavior_blob = _safe_bound_file(
        root_path, surface.get("behavior"), "surface.behavior"
    )
    behavior = _read_json(behavior_path)
    bindings = behavior.get("runtime_bindings")
    if not isinstance(bindings, Mapping):
        raise BoundRuntimeDispatchError("RUNTIME_BINDINGS_INVALID")
    runtime_path, runtime_blob = _safe_bound_file(
        root_path, bindings.get(runtime_key), "runtime." + runtime_key
    )
    return {
        "runtime_key": runtime_key,
        "runtime_path": str(runtime_path),
        "runtime_rel": str(runtime_path.relative_to(root_path)),
        "runtime_git_blob_sha": runtime_blob,
        "behavior_path": str(behavior_path.relative_to(root_path)),
        "behavior_git_blob_sha": behavior_blob,
        "surface_rel": surface_rel,
    }
