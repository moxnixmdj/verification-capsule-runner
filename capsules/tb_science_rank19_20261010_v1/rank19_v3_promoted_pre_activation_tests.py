#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
CLAIM_DIGEST = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
AUTH_BLOB = "31cd7ac44fcdac4dbf1dbcc3e9509aa263d64eac"
LEDGER_BLOB = "62a9aeccbdeea3dd8f51446ddfdd65f993c1c282"
EPOCH_BLOB = "7caf4cd8239f2f47e35889aea8010c00fd9394ed"
CLAIM_BLOB = "b7d11231103a45a2ae16b8e4e64e41b9a801001d"
BRAIN_AUTH_BLOB = "95f4cd33804af167ce11088467883858e9e0a042"
BRAIN_LEDGER_BLOB = "2bb3967dfe894d1dd0e11e190a956faf1fdfcc46"


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
    assert s["family"] == "TB_SCIENCE"
    assert s["active"] is True
    assert s["slot_id"] == SLOT and s["task_digest"] == DIGEST
    assert s["logical_attempt_id"] == ATTEMPT
    assert s["execution_claim_binding_digest"] == CLAIM_DIGEST

    assert s["execution_authority"] is True
    assert s["task_read_authority"] is True
    assert s["task_read_history"] is False
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"] == 0
    assert s["terminal_credit_delta"] == 0

    activation = ROOT / s["activation_path"]
    assert not activation.exists(), "ACTIVATION_MUST_REMAIN_ABSENT_DURING_PROMOTION_PROOF"

    for key in (
        "behavior", "authority", "ledger", "invariant_registry",
        "admission_guard", "epoch", "execution_claim",
        "preflight", "finalizer", "logical_attempt_claim_binding",
    ):
        require_binding(s[key], "surface." + key)

    assert s["authority"]["git_blob_sha"] == AUTH_BLOB
    assert s["ledger"]["git_blob_sha"] == LEDGER_BLOB
    assert s["epoch"]["git_blob_sha"] == EPOCH_BLOB
    assert s["execution_claim"]["git_blob_sha"] == CLAIM_BLOB

    a = load(s["authority"]["path"])
    assert a["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK19_PUBLIC_AUTHORITY_BINDING_V3"
    assert a["slot_id"] == SLOT and a["task_digest"] == DIGEST
    assert a["logical_attempt_id"] == ATTEMPT
    assert a["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert a["brain_authority"]["git_blob_sha"] == BRAIN_AUTH_BLOB
    assert a["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER_BLOB
    assert a["ledger"]["git_blob_sha"] == LEDGER_BLOB
    assert a["execution_authority"] is True
    assert a["task_read_authority"] is True
    assert a["activation_authority"] is False
    assert a["task_read_history"] is False
    assert a["task_started"] is False
    assert a["benchmark_trials_consumed"] == 0

    l = load(s["ledger"]["path"])
    assert l["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK19_PUBLIC_LEDGER_BINDING_V40"
    assert l["brain_authority"]["git_blob_sha"] == BRAIN_AUTH_BLOB
    assert l["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER_BLOB
    assert l["logical_attempt_id"] == ATTEMPT
    assert l["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert l["rank19_task_read_history"] is False
    assert l["rank19_task_started"] is False
    assert l["rank19_start_cas_acquired"] is False
    assert l["rank19_benchmark_trials_consumed"] == 0
    assert l["activation_present"] is False

    e = load(s["epoch"]["path"])
    c = load(s["execution_claim"]["path"])
    assert e["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK19_EPOCH_V7"
    assert c["schema"] == "PROJECT_BRAIN_TB_SCIENCE_RANK19_EXECUTION_CLAIM_V7"
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
    assert c["public_authority_binding_blob"] == AUTH_BLOB
    assert c["public_ledger_binding_blob"] == LEDGER_BLOB
    assert c["epoch_git_blob_sha"] == EPOCH_BLOB

    b = load(s["behavior"]["path"])
    facts = b["behavior"]
    for key in (
        "slot_bound_logical_attempt_identity",
        "execution_claim_bound_logical_attempt_identity",
        "execution_claim_binding_digest_required",
        "execution_claim_epoch_reauthorization_changes_logical_attempt_identity",
        "agent_ready_precedes_start_cas",
        "durable_action_intent_ack_before_effect",
        "durable_state_commit_ack_before_next_action",
        "uncertain_effect_replay_forbidden",
    ):
        assert facts.get(key) is True, key

    inv = load(s["invariant_registry"]["path"])
    ids = {x["id"] for x in inv["invariants"]}
    assert "TB_SCIENCE_CLAIM_BOUND_LOGICAL_ATTEMPT_IDENTITY_V1" in ids

    print("PASS__RANK19_PROMOTED_EFFECTIVE_AUTHORITY__PREACTIVATION__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
