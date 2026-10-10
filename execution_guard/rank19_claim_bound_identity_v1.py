from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id

BASIS = "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"
_CLAIM_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ATTEMPT_RE = re.compile(r"^[0-9a-f]{64}$")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _safe(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        raise RuntimeError("BOUND_PATH_INVALID")
    root = root.resolve()
    path = (root / rel).resolve()
    if path == root or root not in path.parents:
        raise RuntimeError("BOUND_PATH_ESCAPE:" + rel)
    if not path.is_file():
        raise RuntimeError("BOUND_FILE_MISSING:" + rel)
    return path


def resolve_claim_bound_identity(
    *,
    root: Path,
    surface_rel: str,
    expected_slot_id: str,
    expected_task_digest: str,
) -> dict[str, str]:
    root = root.resolve()
    surface_path = _safe(root, surface_rel)
    surface = _read_json(surface_path)
    if (
        surface.get("slot_id") != expected_slot_id
        or surface.get("task_digest") != expected_task_digest
    ):
        raise RuntimeError("SURFACE_SLOT_OR_DIGEST_MISMATCH")

    row = surface.get("authority")
    if not isinstance(row, dict):
        raise RuntimeError("AUTHORITY_BINDING_MISSING")
    rel = row.get("path")
    expected_blob = row.get("git_blob_sha")
    if not isinstance(rel, str) or not isinstance(expected_blob, str):
        raise RuntimeError("AUTHORITY_BINDING_INVALID")
    authority_path = _safe(root, rel)
    if _git_blob(authority_path) != expected_blob:
        raise RuntimeError("AUTHORITY_BLOB_MISMATCH")

    authority = _read_json(authority_path)
    if (
        authority.get("slot_id") != expected_slot_id
        or authority.get("task_digest") != expected_task_digest
    ):
        raise RuntimeError("AUTHORITY_SLOT_OR_DIGEST_MISMATCH")
    if authority.get("logical_attempt_identity_basis") != BASIS:
        raise RuntimeError("AUTHORITY_IDENTITY_BASIS_INVALID")

    claim_digest = authority.get("execution_claim_binding_digest")
    attempt = authority.get("logical_attempt_id")
    if not isinstance(claim_digest, str) or _CLAIM_DIGEST_RE.fullmatch(claim_digest) is None:
        raise RuntimeError("AUTHORITY_CLAIM_BINDING_DIGEST_INVALID")
    if not isinstance(attempt, str) or _ATTEMPT_RE.fullmatch(attempt) is None:
        raise RuntimeError("AUTHORITY_LOGICAL_ATTEMPT_ID_INVALID")

    derived = logical_attempt_id(
        slot_id=expected_slot_id,
        task_digest=expected_task_digest,
        execution_claim_binding_digest=claim_digest,
    )
    if derived != attempt:
        raise RuntimeError("AUTHORITY_LOGICAL_ATTEMPT_ID_DERIVATION_MISMATCH")

    out = {
        "logical_attempt_id": attempt,
        "logical_attempt_identity_basis": BASIS,
        "execution_claim_binding_digest": claim_digest,
    }
    claim_epoch_id = authority.get("claim_epoch_id")
    if isinstance(claim_epoch_id, str) and claim_epoch_id:
        out["claim_epoch_id"] = claim_epoch_id
    return out


__all__ = ["BASIS", "resolve_claim_bound_identity"]
