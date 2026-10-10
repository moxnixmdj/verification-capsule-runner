#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

from execution_guard.rank20_claim_bound_identity_v1 import resolve_claim_bound_identity

ROOT=Path(__file__).resolve().parents[2]
SLOT="terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST="sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
BRANCH="execute/tb-science-rank20-20261010-v1"
ACTIVATION="ACTIVATE_RANK20_V1_PR.json"
PLANNER_SHA="e5d6ab78b6cf5bacee568cd3701410a8745b9ce8"
AGENT_SHA="8deede8adb960b6ebf7ee747a5e9ff1016238b7e"

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def require_binding(row):
    assert isinstance(row,dict), row
    assert blob(row["path"])==row["git_blob_sha"], row

def main():
    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["family"]=="TB_SCIENCE"
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["workflow_path"]==".github/workflows/execute-tb-science-rank20-20261010-v1.yml"
    assert s["activation_path"].endswith(ACTIVATION)
    assert not (ROOT/s["activation_path"]).exists()
    assert s["task_read_history"] is False
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"]==0
    identity=resolve_claim_bound_identity(
        root=ROOT,
        surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",
        expected_slot_id=SLOT,
        expected_task_digest=DIGEST,
    )
    attempt=identity["logical_attempt_id"]
    assert identity["logical_attempt_identity_basis"]=="SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"

    for key in ("behavior","authority","ledger","invariant_registry","admission_guard",
                "epoch","execution_claim","preflight","finalizer"):
        require_binding(s[key])

    b=load(s["behavior"]["path"])
    assert b["slot_id"]==SLOT and b["task_digest"]==DIGEST
    assert b["runtime_bindings"]["planner"]["git_blob_sha"]==PLANNER_SHA
    assert b["runtime_bindings"]["agent"]["git_blob_sha"]==AGENT_SHA
    for row in b["runtime_bindings"].values():
        if isinstance(row,dict) and "path" in row and "git_blob_sha" in row:
            require_binding(row)

    a=load(s["authority"]["path"])
    assert a["slot_id"]==SLOT and a["task_digest"]==DIGEST
    assert a["logical_attempt_id"]==attempt
    assert a["execution_branch"]==BRANCH
    assert a["activation_filename"]==ACTIVATION

    l=load(s["ledger"]["path"])
    assert l["next_slot"]["slot_id"]==SLOT
    assert l["next_slot"]["task_digest"]==DIGEST
    assert l["logical_attempt_id"]==attempt
    assert l["rank20_task_read_history"] is False
    assert l["rank20_task_started"] is False
    assert l["rank20_start_cas_acquired"] is False
    assert l["rank20_benchmark_trials_consumed"]==0

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for doc in (e,c):
        assert doc["slot_id"]==SLOT and doc["task_digest"]==DIGEST
        assert doc["logical_attempt_id"]==attempt
        assert doc["execution_branch"]==BRANCH

    wf=(ROOT/s["workflow_path"]).read_text(encoding="utf-8")
    assert "group: tb-science-terminal-durable-one-shot-global" in wf
    assert BRANCH in wf
    assert ACTIVATION in wf

    identity_expectations = {
        "capsules/tb_science_rank20_20261010_v1/rank20_prestart_token_guard_v5.py":
            ("terminal-bench-science/hysteretic-aquifer-control", DIGEST.split(":",1)[1]),
        "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v7.py":
            (SLOT, DIGEST.split(":",1)[1]),
        "capsules/tb_science_rank20_20261010_v1/rank20_v7_status_journal_runner.py":
            (SLOT, DIGEST.split(":",1)[1]),
        "capsules/tb_science_rank20_20261010_v1/rank20_finalize_receipt_v7.py":
            (SLOT, DIGEST.split(":",1)[1]),
        "capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v7.py":
            (SLOT, DIGEST.split(":",1)[1]),
    }
    for rel, expected in identity_expectations.items():
        text=(ROOT/rel).read_text(encoding="utf-8")
        assert "RANK18" not in text and "rank18" not in text
        assert all(fragment in text for fragment in expected), (rel, expected)

    assert b["behavior"]["execution_claim_bound_logical_attempt_identity"] is True
    assert b["runtime_bindings"]["identity_primitive"]["path"]=="execution_guard/logical_attempt_identity_v2.py"
    assert b["runtime_bindings"]["claim_bound_identity_resolver"]["path"]=="execution_guard/rank20_claim_bound_identity_v1.py"

    print("PASS__TB_SCIENCE_RANK20_V2_V13_CLAIM_BOUND_PUBLIC_RESEAL__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
