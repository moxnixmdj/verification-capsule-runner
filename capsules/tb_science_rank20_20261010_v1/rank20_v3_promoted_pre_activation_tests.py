#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
ATTEMPT = "62bbf27ddcc679f431c5569244cf0c54fb1b13181e83076e2c019764f0b747e2"
CLAIM_DIGEST = "sha256:ad74fd461333c1673b76ec0b439aba98c35bf6a0691796b24a5847209873adba"
AUTH_BLOB = "a9502035da90e9a7c3bbc26859794d99632fe8f4"
LEDGER_BLOB = "fd61b24b76065aae96986b12e99bd34c72a2ffac"
EPOCH_BLOB = "79d9ff740c72121f6e76c6577f07dbda28135105"
CLAIM_BLOB = "b5c5afd8997f62c2cf79bade40376e5d326b98d3"
BRAIN_AUTH_BLOB = "6720cd2ea9ca70f6cf1b4a26036c935759842140"
BRAIN_LEDGER_BLOB = "fb20c82a5b7f8c7738a526905d51cab5c7994a5a"
CLAIM_BINDING_BLOB = "59fa5616f1754f90ded1c3b30cb53c98b4348cee"
CLAIM_SEED_BEHAVIOR = "9012d4bf1c84e157cdfa27ec04fd1a5afd7c78c7"
EFFECTIVE_BEHAVIOR = "dc20b4ef740eaeb6741c834d9c74634653c69193"
REFINEMENT_VERIFIER = "b15a9d9ba3a717a9758f56aef75e5e14764d9221"


def load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(value, dict), rel
    return value


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require_binding(row: Any, label: str) -> str:
    assert isinstance(row, Mapping), (label, row)
    rel = row.get("path")
    sha = row.get("git_blob_sha")
    assert isinstance(rel, str) and isinstance(sha, str), (label, row)
    assert (ROOT / rel).is_file(), (label, rel)
    assert blob(rel) == sha, (label, rel, blob(rel), sha)
    return rel


def main() -> int:
    s = load(SURFACE_REL)
    assert s["schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1"
    assert s["family"] == "TB_SCIENCE" and s["active"] is True
    assert s["slot_id"] == SLOT and s["task_digest"] == DIGEST
    assert s["logical_attempt_id"] == ATTEMPT
    assert s["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert s["execution_authority"] is True
    assert s["task_read_authority"] is True
    assert s["task_read_history"] is False
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"] == 0
    assert s["terminal_credit_delta"] == 0
    assert not (ROOT / s["activation_path"]).exists()

    for key in (
        "behavior", "authority", "ledger", "invariant_registry", "admission_guard",
        "epoch", "execution_claim", "preflight", "finalizer",
        "logical_attempt_claim_binding", "behavior_refinement_verification",
    ):
        require_binding(s[key], "surface." + key)

    assert s["authority"]["git_blob_sha"] == AUTH_BLOB
    assert s["ledger"]["git_blob_sha"] == LEDGER_BLOB
    assert s["epoch"]["git_blob_sha"] == EPOCH_BLOB
    assert s["execution_claim"]["git_blob_sha"] == CLAIM_BLOB
    assert s["behavior"]["git_blob_sha"] == EFFECTIVE_BEHAVIOR
    assert s["logical_attempt_claim_binding"]["git_blob_sha"] == CLAIM_BINDING_BLOB
    assert s["behavior_refinement_verification"]["git_blob_sha"] == REFINEMENT_VERIFIER

    a = load(s["authority"]["path"])
    assert a["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_AUTHORITY_BINDING_V3"
    assert a["brain_authority"]["git_blob_sha"] == BRAIN_AUTH_BLOB
    assert a["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER_BLOB
    assert a["ledger"]["git_blob_sha"] == LEDGER_BLOB
    assert a["claim_seed_behavior"]["git_blob_sha"] == CLAIM_SEED_BEHAVIOR
    assert a["behavior"]["git_blob_sha"] == EFFECTIVE_BEHAVIOR
    assert a["execution_authority"] is True
    assert a["task_read_authority"] is True
    assert a["activation_authority"] is False
    assert a["task_read_history"] is False
    assert a["task_started"] is False
    assert a["benchmark_trials_consumed"] == 0

    l = load(s["ledger"]["path"])
    assert l["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_LEDGER_BINDING_V44"
    assert l["brain_authority"]["git_blob_sha"] == BRAIN_AUTH_BLOB
    assert l["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER_BLOB
    assert l["logical_attempt_id"] == ATTEMPT
    assert l["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert l["rank20_task_read_history"] is False
    assert l["rank20_task_started"] is False
    assert l["rank20_start_cas_acquired"] is False
    assert l["rank20_benchmark_trials_consumed"] == 0
    assert l["activation_present"] is False

    e = load(s["epoch"]["path"])
    c = load(s["execution_claim"]["path"])
    assert e["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK20_EPOCH_V6"
    assert c["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK20_EXECUTION_CLAIM_V6"
    for doc in (e, c):
        assert doc["slot_id"] == SLOT and doc["task_digest"] == DIGEST
        assert doc["logical_attempt_id"] == ATTEMPT
        assert doc["execution_claim_binding_digest"] == CLAIM_DIGEST
        assert doc["brain_authority_blob"] == BRAIN_AUTH_BLOB
        assert doc["brain_ledger_blob"] == BRAIN_LEDGER_BLOB
        assert doc["execution_authority"] is True
        assert doc["execution_authority_effective"] is True
        assert doc["task_read_authority"] is True
        assert doc["activation_present"] is False

    assert e["public_authority_binding_blob"] == AUTH_BLOB
    assert e["public_ledger_binding_blob"] == LEDGER_BLOB
    assert e["behavior_blob"] == EFFECTIVE_BEHAVIOR
    assert e["claim_seed_behavior_blob"] == CLAIM_SEED_BEHAVIOR
    assert c["public_authority_binding_blob"] == AUTH_BLOB
    assert c["public_ledger_binding_blob"] == LEDGER_BLOB
    assert c["epoch_git_blob_sha"] == EPOCH_BLOB
    assert c["behavior_git_blob_sha"] == EFFECTIVE_BEHAVIOR
    assert c["claim_seed_behavior_git_blob_sha"] == CLAIM_SEED_BEHAVIOR

    # Re-run the proof-only refinement theorem in its normal file context.
    verifier_rel = s["behavior_refinement_verification"]["path"]
    subprocess.check_call([sys.executable, str(ROOT / verifier_rel)])

    print("PASS__RANK20_PROMOTED_EFFECTIVE_AUTHORITY__PREACTIVATION__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
