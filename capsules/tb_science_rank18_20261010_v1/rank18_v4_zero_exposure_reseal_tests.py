#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SLOT="terminal-bench-science/longitudinal-clinical-agent::trial-0"
DIGEST="sha256:e9a166b2173f7014d4f1559505397b221f94bc446eab031f94791b35e0e5f1c9"
ATTEMPT="a02ee7de469f953679fb593ab152a9f67eb1ebe8c364f8c748f18cd8a81eab8d"
FRESH_BRANCH="execute/tb-science-rank18-20261010-v2"
RETIRED_BRANCH="execute/tb-science-rank18-20261010-v1"
FRESH_ACTIVATION="ACTIVATE_RANK18_V2_PR.json"

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
    assert s["schema"]=="PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1"
    assert s["family"]=="TB_SCIENCE"
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["active"] is True and s["execution_authority"] is True
    assert s["task_read_authority"] is True and s["task_read_history"] is True
    assert s["task_started"] is False and s["benchmark_trials_consumed"]==0
    assert s["workflow_path"]==".github/workflows/execute-tb-science-rank18-20261010-v2.yml"
    assert s["activation_path"].endswith(FRESH_ACTIVATION)
    assert not (ROOT/s["activation_path"]).exists()
    assert not (ROOT/"capsules/tb_science_rank18_20261010_v1/ACTIVATE_RANK18_V1_PR.json").exists()

    for key in ("behavior","authority","ledger","invariant_registry","admission_guard",
                "epoch","execution_claim","preflight","finalizer"):
        require_binding(s[key])

    b=load(s["behavior"]["path"])
    assert b["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK18_EXECUTION_BEHAVIOR_V4"
    assert b["workflow_path"]==s["workflow_path"]
    assert b["runtime_bindings"]["status_journal_runner"]["git_blob_sha"]=="d1bb9fc6766f16b34a955c6f1b41d2da0b2709df"
    assert b["runtime_bindings"]["start_cas"]["git_blob_sha"]=="36d220f5caaee9f52fe9dd6f5dac1cbac774d3b1"
    assert b["runtime_bindings"]["preflight"]["git_blob_sha"]=="b0b6cb702f03ae5165afaeb81c59a60c93972c5e"
    for row in b["runtime_bindings"].values():
        if isinstance(row,dict) and "path" in row and "git_blob_sha" in row:
            require_binding(row)

    a=load(s["authority"]["path"])
    assert a["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK18_PUBLIC_AUTHORITY_BINDING_V4"
    assert a["brain_authority"]["git_blob_sha"]=="7ab3d1d294d82192462c735ff7cb7e0dc3abc06f"
    assert a["brain_ledger"]["git_blob_sha"]=="73ad3e6e2b9cb9e1f3b72c3f08d6842814ca1940"
    assert a["repair_verification"]["git_blob_sha"]=="aec85d3a6b82aa8ab7a6942b535838333195fb9c"
    assert a["execution_branch"]==FRESH_BRANCH
    assert a["activation_filename"]==FRESH_ACTIVATION

    l=load(s["ledger"]["path"])
    assert l["rank18_task_read_history"] is True
    assert l["rank18_task_started"] is False
    assert l["rank18_start_cas_acquired"] is False
    assert l["rank18_benchmark_trials_consumed"]==0
    assert l["logical_attempt_id"]==ATTEMPT

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for doc in (e,c):
        assert doc["slot_id"]==SLOT and doc["task_digest"]==DIGEST
        assert doc["logical_attempt_id"]==ATTEMPT
        assert doc["execution_branch"]==FRESH_BRANCH
    assert e["task_read_history_before_epoch"] is True
    assert c["task_read_history_before_claim"] is True
    assert c["activation_filename"]==FRESH_ACTIVATION
    assert c["epoch_git_blob_sha"]==s["epoch"]["git_blob_sha"]
    assert c["behavior_git_blob_sha"]==s["behavior"]["git_blob_sha"]
    assert c["public_authority_binding_blob"]==s["authority"]["git_blob_sha"]

    start=(ROOT/"capsules/tb_science_rank18_20261010_v1/rank18_start_cas_v6.py").read_text()
    preflight=(ROOT/"capsules/tb_science_rank18_20261010_v1/rank18_execution_preflight_v6.py").read_text()
    assert FRESH_BRANCH in start and RETIRED_BRANCH not in start
    assert FRESH_ACTIVATION in start and "ACTIVATE_RANK18_V1_PR.json" not in start
    assert FRESH_BRANCH in preflight and RETIRED_BRANCH not in preflight
    assert FRESH_ACTIVATION in preflight and "ACTIVATE_RANK18_V1_PR.json" not in preflight

    print("PASS__TB_SCIENCE_RANK18_V4_FRESH_ACTIVATION_BRANCH_RESEAL__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
