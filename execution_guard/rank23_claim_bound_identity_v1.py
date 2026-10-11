#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id

class ClaimBoundIdentityError(RuntimeError):
    pass

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _read(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ClaimBoundIdentityError("JSON_OBJECT_REQUIRED")
    return value

def _safe(root:Path,rel:str)->Path:
    if not isinstance(rel,str) or not rel or rel.startswith("/"):
        raise ClaimBoundIdentityError("PATH_INVALID")
    p=(root/rel).resolve()
    if p==root.resolve() or root.resolve() not in p.parents or not p.is_file():
        raise ClaimBoundIdentityError("PATH_INVALID_OR_MISSING")
    return p

def resolve_claim_bound_identity(*,root:Path,surface_rel:str,expected_slot_id:str,expected_task_digest:str)->dict[str,str]:
    surface_path=_safe(root,surface_rel)
    surface=_read(surface_path)
    if surface.get("slot_id")!=expected_slot_id or surface.get("task_digest")!=expected_task_digest:
        raise ClaimBoundIdentityError("SURFACE_SLOT_OR_DIGEST_MISMATCH")
    row=surface.get("logical_attempt_claim_binding")
    if not isinstance(row,dict):
        raise ClaimBoundIdentityError("CLAIM_BINDING_REQUIRED")
    path=_safe(root,row.get("path"))
    expected_blob=row.get("git_blob_sha")
    if _blob(path)!=expected_blob:
        raise ClaimBoundIdentityError("CLAIM_BINDING_BLOB_MISMATCH")
    claim=_read(path)
    if claim.get("slot_id")!=expected_slot_id or claim.get("task_digest")!=expected_task_digest:
        raise ClaimBoundIdentityError("CLAIM_SLOT_OR_DIGEST_MISMATCH")
    raw=json.dumps(claim,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    digest="sha256:"+hashlib.sha256(raw).hexdigest()
    if surface.get("execution_claim_binding_digest")!=digest:
        raise ClaimBoundIdentityError("SURFACE_CLAIM_DIGEST_MISMATCH")
    attempt=logical_attempt_id(
        slot_id=expected_slot_id,
        task_digest=expected_task_digest,
        execution_claim_binding_digest=digest,
    )
    if surface.get("logical_attempt_id")!=attempt:
        raise ClaimBoundIdentityError("SURFACE_LOGICAL_ATTEMPT_ID_MISMATCH")
    return {
        "logical_attempt_id":attempt,
        "execution_claim_binding_digest":digest,
        "logical_attempt_identity_basis":"SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST",
        "claim_binding_git_blob_sha":expected_blob,
    }
