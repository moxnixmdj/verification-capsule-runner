#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"capsules/tb_science_rank17_20261009_v4"
SLOT="terminal-bench-science/variable-star-vetting::trial-0"
DIGEST="sha256:51bf2b9d8e87a428772d92c6765d83ad3edc7c24283d2ff75af5f050aaee0c67"
WORKFLOW=".github/workflows/execute-tb-science-rank17-20261009-v4.yml"
RAW_BLOB="53a440fccf91aa08f18abfff4f283e5fd18d9fcd"
INDEX_BLOB="525fac941302254a47710aaae30b0174fab2cb40"
BRAIN_AUTHORITY="1f0e1e7739eeaff67cac8ca5781a94c0f6ea8cf9"
BRAIN_AUTHORITY_VERIFY="d41a4f2e32f7ba94ea5dcc78aad8bc0a73394826"
BRAIN_LEDGER="9c2f95b2d7946e374811321cde58d11f53704fd2"
BRAIN_REPAIR_VERIFY="28ec71862357908bd2c868ca6494a9d89439a223"

def blob(rel):
    p=ROOT/rel; raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def main():
    assert not (CAP/"ACTIVATE_RANK17_V4_PR.json").exists()

    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["active"] is True
    assert s["execution_authority"] is True
    assert s["task_read_authority"] is True
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"] == 0
    assert s["slot_id"] == SLOT and s["task_digest"] == DIGEST
    assert s["workflow_path"] == WORKFLOW
    assert s["activation_path"] == "capsules/tb_science_rank17_20261009_v4/ACTIVATE_RANK17_V4_PR.json"

    for key in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer"):
        assert blob(s[key]["path"]) == s[key]["git_blob_sha"], key
    assert blob(WORKFLOW) == s["workflow_git_blob_sha"]

    b=load(s["behavior"]["path"])
    rb=b["runtime_bindings"]
    assert rb["lossless_raw_task_contract"]["git_blob_sha"] == RAW_BLOB
    assert rb["explicit_requirement_index"]["git_blob_sha"] == INDEX_BLOB
    assert blob(rb["lossless_raw_task_contract"]["path"]) == RAW_BLOB
    assert blob(rb["explicit_requirement_index"]["path"]) == INDEX_BLOB
    assert rb["agent"]["git_blob_sha"] == "124d13a7449281c9781c39df8f02c2e8f74226b4"
    assert rb["planner"]["git_blob_sha"] == "ecfaa7523347ba0e902baa9d411e333d3e2853e4"
    assert "harbor_science_agent_v11.py" in rb["agent"]["path"]

    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"] == BRAIN_AUTHORITY
    assert a["brain_authority_verification"]["git_blob_sha"] == BRAIN_AUTHORITY_VERIFY
    assert a["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER
    assert a["brain_repair_verification"]["git_blob_sha"] == BRAIN_REPAIR_VERIFY
    assert a["execution_branch"] == "execute/tb-science-rank17-20261009-v4"
    assert a["activation_filename"] == "ACTIVATE_RANK17_V4_PR.json"
    assert a["task_read_history"] is True
    assert a["task_started"] is False and a["benchmark_trials_consumed"] == 0
    assert a["public_reseal_satisfies_brain_v4_task_read_prerequisite"] is True

    l=load(s["ledger"]["path"])
    assert l["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER
    assert l["consumed_slots"] == 16
    assert l["rank17_task_read_history"] is True
    assert l["rank17_task_started"] is False
    assert l["rank17_benchmark_trials_consumed"] == 0

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for x in (e,c):
        assert x["slot_id"] == SLOT and x["task_digest"] == DIGEST
        assert x["execution_branch"] == "execute/tb-science-rank17-20261009-v4"
    assert c["activation_filename"] == "ACTIVATE_RANK17_V4_PR.json"
    assert c["lossless_raw_task_contract_git_blob_sha"] == RAW_BLOB
    assert c["explicit_requirement_index_git_blob_sha"] == INDEX_BLOB

    q=load("execution_guard/TB_SCIENCE_RANK15_CONSUMED_PUBLIC_QUARANTINE_V1.json")
    assert q["quarantine"]["rank15_replay_authority"] is False
    assert q["quarantine"]["rank15_replacement_authority"] is False

    print("PASS__TB_SCIENCE_RANK17_V4_ZERO_EXPOSURE_RESEAL__REPAIRED_RAW_TASK_RUNTIME_BOUND")

if __name__=="__main__":
    main()
