from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as derive_logical_attempt_id
BINDING_REL = "capsules/tb_science_rank19_20261010_v1/RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_V1.json"
BINDING_PATH = ROOT / BINDING_REL
SLOT_ID = "terminal-bench-science/diag-chipseq::trial-0"
TASK_DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM_EPOCH_ID = "RANK19_V14_CLAIM_BOUND_IDENTITY_20261010_V1"
EXPECTED_CANONICAL_SHA256 = "4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
EXPECTED_GIT_BLOB_SHA = "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"
EXECUTION_CLAIM_BINDING_DIGEST = "sha256:" + EXPECTED_CANONICAL_SHA256
EXPECTED_LOGICAL_ATTEMPT_ID = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


class Rank19LogicalAttemptBindingError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_claim_binding() -> dict[str, Any]:
    raw = BINDING_PATH.read_bytes()
    if _git_blob_sha(raw) != EXPECTED_GIT_BLOB_SHA:
        raise Rank19LogicalAttemptBindingError("CLAIM_BINDING_GIT_BLOB_MISMATCH")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise Rank19LogicalAttemptBindingError("CLAIM_BINDING_OBJECT_REQUIRED")
    checks = {
        "schema": value.get("schema") == "PROJECT_BRAIN_TB_SCIENCE_RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_V1",
        "claim_epoch_id": value.get("claim_epoch_id") == CLAIM_EPOCH_ID,
        "slot_id": value.get("slot_id") == SLOT_ID,
        "task_digest": value.get("task_digest") == TASK_DIGEST,
        "execution_base": value.get("execution_base") == "terminal-execution-v1",
        "execution_branch": value.get("execution_branch") == "execute/tb-science-rank19-20261010-v1",
        "activation_filename": value.get("activation_filename") == "ACTIVATE_RANK19_V1_PR.json",
        "brain_authority_blob": value.get("brain_authority_blob") == "54b4b41872cce41ed1bdc6181d857484a2f21b22",
        "brain_ledger_blob": value.get("brain_ledger_blob") == "137a2f61d911321365bd80613e3806a77dbe7eca",
        "capability_first_checkpoint_admission_blob": value.get("capability_first_checkpoint_admission_blob") == "49e4f9c232f876546b2c72fb32ba19a3e487e1c9",
        "capability_first_admission_verification_blob": value.get("capability_first_admission_verification_blob") == "7ba01fca8338d966a40f25a8c74f6e1366b29f2e",
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise Rank19LogicalAttemptBindingError("CLAIM_BINDING_FIELD_MISMATCH:" + ",".join(failed))
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    if digest != EXPECTED_CANONICAL_SHA256:
        raise Rank19LogicalAttemptBindingError("CLAIM_BINDING_CANONICAL_SHA256_MISMATCH")
    return value


def execution_claim_binding_digest() -> str:
    load_claim_binding()
    return EXECUTION_CLAIM_BINDING_DIGEST


def logical_attempt_id() -> str:
    digest = execution_claim_binding_digest()
    actual = derive_logical_attempt_id(
        slot_id=SLOT_ID,
        task_digest=TASK_DIGEST,
        execution_claim_binding_digest=digest,
    )
    if actual != EXPECTED_LOGICAL_ATTEMPT_ID:
        raise Rank19LogicalAttemptBindingError("LOGICAL_ATTEMPT_ID_DERIVATION_MISMATCH")
    return actual
