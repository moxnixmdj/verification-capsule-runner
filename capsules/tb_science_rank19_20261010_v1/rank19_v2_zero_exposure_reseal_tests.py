#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM_DIGEST = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
BRANCH = "execute/tb-science-rank19-20261010-v1"
ACTIVATION = "ACTIVATE_RANK19_V1_PR.json"
CLAIM_BINDING_REL = "capsules/tb_science_rank19_20261010_v1/RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_V1.json"
IDENTITY_V2_REL = "execution_guard/logical_attempt_identity_v2.py"
HELPER_REL = "capsules/tb_science_rank19_20261010_v1/rank19_logical_attempt_binding_v1.py"


def load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(value, dict), rel
    return value


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require_binding(row: Any) -> None:
    assert isinstance(row, dict), row
    assert blob(row["path"]) == row["git_blob_sha"], row


def main() -> int:
    claim_seed = load(CLAIM_BINDING_REL)
    assert blob(CLAIM_BINDING_REL) == "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"
    assert canonical_sha256(claim_seed) == CLAIM_DIGEST.split(":", 1)[1]
    assert claim_seed["slot_id"] == SLOT
    assert claim_seed["task_digest"] == DIGEST
    assert claim_seed["claim_epoch_id"] == "RANK19_V14_CLAIM_BOUND_IDENTITY_20261010_V1"

    identity_material = {
        "schema": "PROJECT_BRAIN_LOGICAL_ATTEMPT_IDENTITY_V2",
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "execution_claim_binding_digest": CLAIM_DIGEST,
    }
    assert canonical_sha256(identity_material) == ATTEMPT

    s = load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["family"] == "TB_SCIENCE"
    assert s["slot_id"] == SLOT and s["task_digest"] == DIGEST
    assert s["workflow_path"] == ".github/workflows/execute-tb-science-rank19-20261010-v1.yml"
    assert s["activation_path"].endswith(ACTIVATION)
    assert not (ROOT / s["activation_path"]).exists()
    assert s["task_read_history"] is False
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"] == 0
    assert s["execution_authority"] is False
    assert s["task_read_authority"] is False
    assert s["logical_attempt_id"] == ATTEMPT
    assert s["execution_claim_binding_digest"] == CLAIM_DIGEST

    for key in (
        "behavior",
        "authority",
        "ledger",
        "invariant_registry",
        "admission_guard",
        "epoch",
        "execution_claim",
        "preflight",
        "finalizer",
        "logical_attempt_claim_binding",
    ):
        require_binding(s[key])

    assert s["logical_attempt_claim_binding"]["path"] == CLAIM_BINDING_REL
    assert s["logical_attempt_claim_binding"]["git_blob_sha"] == "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"

    b = load(s["behavior"]["path"])
    assert b["slot_id"] == SLOT and b["task_digest"] == DIGEST
    assert b["logical_attempt_id"] == ATTEMPT
    assert b["execution_claim_binding_digest"] == CLAIM_DIGEST
    facts = b["behavior"]
    assert facts["slot_bound_logical_attempt_identity"] is True
    assert facts["execution_claim_bound_logical_attempt_identity"] is True
    assert facts["execution_claim_binding_digest_required"] is True
    assert facts["goal_text_excluded_from_logical_attempt_identity"] is True
    assert facts["carrier_identity_excluded_from_logical_attempt_identity"] is True
    assert facts["durable_action_intent_ack_before_effect"] is True
    assert facts["durable_state_commit_ack_before_next_action"] is True
    assert facts["uncertain_effect_replay_forbidden"] is True

    rb = b["runtime_bindings"]
    assert rb["identity_primitive"]["path"] == IDENTITY_V2_REL
    assert rb["logical_attempt_claim_binding"]["path"] == CLAIM_BINDING_REL
    assert rb["logical_attempt_binding_helper"]["path"] == HELPER_REL
    for row in rb.values():
        if isinstance(row, dict) and "path" in row and "git_blob_sha" in row:
            require_binding(row)

    a = load(s["authority"]["path"])
    assert a["slot_id"] == SLOT and a["task_digest"] == DIGEST
    assert a["logical_attempt_id"] == ATTEMPT
    assert a["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert a["execution_branch"] == BRANCH
    assert a["activation_filename"] == ACTIVATION

    l = load(s["ledger"]["path"])
    assert l["next_slot"]["slot_id"] == SLOT
    assert l["next_slot"]["task_digest"] == DIGEST
    assert l["logical_attempt_id"] == ATTEMPT
    assert l["execution_claim_binding_digest"] == CLAIM_DIGEST
    assert l["rank19_task_read_history"] is False
    assert l["rank19_task_started"] is False
    assert l["rank19_start_cas_acquired"] is False
    assert l["rank19_benchmark_trials_consumed"] == 0

    e = load(s["epoch"]["path"])
    c = load(s["execution_claim"]["path"])
    for doc in (e, c):
        assert doc["slot_id"] == SLOT and doc["task_digest"] == DIGEST
        assert doc["logical_attempt_id"] == ATTEMPT
        assert doc["execution_claim_binding_digest"] == CLAIM_DIGEST
        assert doc["execution_branch"] == BRANCH

    wf = (ROOT / s["workflow_path"]).read_text(encoding="utf-8")
    required = (
        "terminal_execution_admission_v4.py",
        "rank19_execution_preflight_v7.py",
        "rank19_start_cas_v7.py",
        "rank19_prestart_token_guard_v5.py",
        "rank19_v7_status_journal_runner.py",
        "rank19_finalize_receipt_v7.py",
        "group: tb-science-terminal-durable-one-shot-global",
    )
    for marker in required:
        assert marker in wf, marker
    forbidden = (
        "terminal_execution_admission_v3.py",
        "rank19_execution_preflight_v6.py",
        "rank19_start_cas_v6.py",
        "rank19_prestart_token_guard_v4.py",
        "rank19_v6_status_journal_runner.py",
        "rank19_finalize_receipt_v6.py",
    )
    for marker in forbidden:
        assert marker not in wf, marker

    for rel in (
        "capsules/tb_science_rank19_20261010_v1/rank19_prestart_token_guard_v5.py",
        "capsules/tb_science_rank19_20261010_v1/rank19_start_cas_v7.py",
        "capsules/tb_science_rank19_20261010_v1/rank19_v7_status_journal_runner.py",
        "capsules/tb_science_rank19_20261010_v1/rank19_finalize_receipt_v7.py",
        "capsules/tb_science_rank19_20261010_v1/rank19_execution_preflight_v7.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert ATTEMPT not in text or rel.endswith("rank19_logical_attempt_binding_v1.py")
        assert "logical_attempt_identity_v1" not in text

    print("PASS__TB_SCIENCE_RANK19_V14_CLAIM_BOUND_IDENTITY_PUBLIC_RESEAL__ZERO_EXPOSURE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
