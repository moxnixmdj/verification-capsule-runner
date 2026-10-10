#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
CLAIM_DIGEST = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
AUTH_V2_BLOB = "6efd0561447446a6bd6bbdb784b7184e50e1f362"
LEDGER_V39_BLOB = "40d63f342a6ff62f0c038aa6b28f8f2d6a7920f3"
BRAIN_V4_BLOB = "95f4cd33804af167ce11088467883858e9e0a042"
BRAIN_V40_BLOB = "2bb3967dfe894d1dd0e11e190a956faf1fdfcc46"
BRAIN_V14_VERIFY_BLOB = "c0a723a39c1fcfb3e25a4d72ef9543f0e8f8f17f"
PUBLIC_V14_COMMIT = "12491be6f20c28027a768352e60550a2b49e3bcd"
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK19_EFFECTIVE_AUTHORITY_PROMOTION_VERIFY_V1"


def load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + rel)
    return value


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require_binding(row: Any, label: str) -> str:
    if not isinstance(row, dict):
        raise RuntimeError("BINDING_MISSING:" + label)
    rel = row.get("path")
    sha = row.get("git_blob_sha")
    if not isinstance(rel, str) or not isinstance(sha, str):
        raise RuntimeError("BINDING_INVALID:" + label)
    if not (ROOT / rel).is_file():
        raise RuntimeError("BINDING_FILE_MISSING:" + label)
    got = blob(rel)
    if got != sha:
        raise RuntimeError(f"BINDING_BLOB_MISMATCH:{label}:{got}:{sha}")
    return rel


def main() -> int:
    surface = load(SURFACE_REL)
    assert surface["schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1"
    assert surface["family"] == "TB_SCIENCE"
    assert surface["active"] is True
    assert surface["slot_id"] == SLOT
    assert surface["task_digest"] == DIGEST
    assert surface["logical_attempt_id"] == ATTEMPT
    assert surface["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert surface["execution_authority"] is True
    assert surface["task_read_authority"] is True
    assert surface["task_read_history"] is False
    assert surface["task_started"] is False
    assert surface["benchmark_trials_consumed"] == 0
    assert surface["terminal_credit_delta"] == 0

    activation = ROOT / surface["activation_path"]
    assert not activation.exists(), "PROMOTION_MUST_NOT_ARM_ACTIVATION"

    authority_rel = require_binding(surface["authority"], "surface.authority")
    ledger_rel = require_binding(surface["ledger"], "surface.ledger")
    assert surface["authority"]["git_blob_sha"] == AUTH_V2_BLOB
    assert surface["ledger"]["git_blob_sha"] == LEDGER_V39_BLOB

    authority = load(authority_rel)
    ledger = load(ledger_rel)
    assert authority["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK19_PUBLIC_AUTHORITY_BINDING_V2"
    assert authority["execution_authority"] is True
    assert authority["logical_attempt_id"] == ATTEMPT
    assert authority["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert authority["task_read_authority"] == "ONLY_AFTER_PUBLIC_RESEAL_VERIFIED_AND_CANONICAL_PROMOTION"
    assert ledger["logical_attempt_id"] == ATTEMPT
    assert ledger["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert ledger["rank19_task_read_history"] is False
    assert ledger["rank19_task_started"] is False
    assert ledger["rank19_start_cas_acquired"] is False
    assert ledger["rank19_benchmark_trials_consumed"] == 0

    for key in (
        "behavior", "invariant_registry", "admission_guard", "epoch",
        "execution_claim", "preflight", "finalizer", "logical_attempt_claim_binding",
    ):
        require_binding(surface[key], "surface." + key)

    basis = surface.get("promotion_basis")
    assert isinstance(basis, dict)
    assert basis["brain_authority_v4_git_blob_sha"] == BRAIN_V4_BLOB
    assert basis["brain_ledger_v40_git_blob_sha"] == BRAIN_V40_BLOB
    assert basis["brain_v14_public_reseal_verification_git_blob_sha"] == BRAIN_V14_VERIFY_BLOB
    assert basis["public_v14_certified_commit_sha"] == PUBLIC_V14_COMMIT
    assert basis["same_claim_bound_logical_attempt"] is True
    assert basis["zero_exposure_promotion_only"] is True

    self_row = surface.get("promotion_verification")
    assert isinstance(self_row, dict)
    assert self_row["path"].endswith("rank19_effective_authority_promotion_v1.py")
    assert blob(self_row["path"]) == self_row["git_blob_sha"]

    preflight = surface["preflight"]["path"]
    before = json.loads((ROOT / SURFACE_REL).read_text(encoding="utf-8"))
    subprocess.check_call([sys.executable, str(ROOT / preflight)])

    admission = surface["admission_guard"]["path"]
    common = [
        sys.executable, str(ROOT / admission),
        "--workflow", surface["workflow_path"],
        "--slot", SLOT,
        "--task-digest", DIGEST,
        "--require-execution-authority",
    ]
    subprocess.check_call(common)
    gated = subprocess.run(common + ["--require-activation"], check=False)
    assert gated.returncode != 0, "ACTIVATION_GATE_MUST_REMAIN_CLOSED"
    receipt = load("TERMINAL_EXECUTION_ADMISSION_V4.json")
    assert "ACTIVATION_FILE_MISSING" in receipt.get("errors", [])

    after = json.loads((ROOT / SURFACE_REL).read_text(encoding="utf-8"))
    assert after == before
    assert not activation.exists()

    out = {
        "schema": SCHEMA,
        "status": "PASS__RANK19_EFFECTIVE_PUBLIC_AUTHORITY_PROMOTION__CLAIM_IDENTITY_PRESERVED__ACTIVATION_GATE_CLOSED__ZERO_EXPOSURE",
        "pass": True,
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "logical_attempt_id": ATTEMPT,
        "execution_authority": True,
        "task_read_authority": True,
        "task_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    (ROOT / "RANK19_EFFECTIVE_AUTHORITY_PROMOTION_VERIFY_V1.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
