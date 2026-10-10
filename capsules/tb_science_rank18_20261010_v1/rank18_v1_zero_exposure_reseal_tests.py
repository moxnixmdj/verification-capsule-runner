#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"capsules/tb_science_rank18_20261010_v1"
SLOT="terminal-bench-science/longitudinal-clinical-agent::trial-0"
DIGEST="sha256:e9a166b2173f7014d4f1559505397b221f94bc446eab031f94791b35e0e5f1c9"
WORKFLOW=".github/workflows/execute-tb-science-rank18-20261010-v1.yml"
RAW_BLOB="53a440fccf91aa08f18abfff4f283e5fd18d9fcd"
INDEX_BLOB="525fac941302254a47710aaae30b0174fab2cb40"
BRAIN_AUTHORITY="0cbf7ffb571c0f411a5ba44c751b1c833059c83c"
BRAIN_AUTHORITY_VERIFY="4c829d9e5dc878fd0ef002221f9b27170c853aa5"
BRAIN_LEDGER="c2d405754e51254aa2eee8e6eb9413a298cdf90b"
BRAIN_REPAIR_VERIFY="6470f6bf071cbf89bfbc95e86eb457cb0d10abdf"

def blob(rel):
    p=ROOT/rel; raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def main():
    assert not (CAP/"ACTIVATE_RANK18_V1_PR.json").exists()

    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["active"] is True
    assert s["execution_authority"] is True
    assert s["task_read_authority"] is True
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"] == 0
    assert s["slot_id"] == SLOT and s["task_digest"] == DIGEST
    assert s["workflow_path"] == WORKFLOW
    assert s["activation_path"] == "capsules/tb_science_rank18_20261010_v1/ACTIVATE_RANK18_V1_PR.json"

    for key in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer"):
        assert blob(s[key]["path"]) == s[key]["git_blob_sha"], key
    assert blob(WORKFLOW) == s["workflow_git_blob_sha"]

    b=load(s["behavior"]["path"])
    rb=b["runtime_bindings"]
    assert rb["lossless_raw_task_contract"]["git_blob_sha"] == RAW_BLOB
    assert rb["explicit_requirement_index"]["git_blob_sha"] == INDEX_BLOB
    assert blob(rb["lossless_raw_task_contract"]["path"]) == RAW_BLOB
    assert blob(rb["explicit_requirement_index"]["path"]) == INDEX_BLOB
    assert rb["agent"]["git_blob_sha"] == "e5ccaab049d22c0b3cc59e36c050ce2f6e83404f"
    assert rb["typed_action_protocol"]["git_blob_sha"] == "fa10b92942b92ab6c7f2f1831f660f2a2e3bd6e3"
    assert rb["planner"]["git_blob_sha"] == "ecfaa7523347ba0e902baa9d411e333d3e2853e4"
    assert "harbor_science_agent_v12.py" in rb["agent"]["path"]

    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"] == BRAIN_AUTHORITY
    assert a["brain_authority_verification"]["git_blob_sha"] == BRAIN_AUTHORITY_VERIFY
    assert a["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER
    assert a["brain_repair_verification"]["git_blob_sha"] == BRAIN_REPAIR_VERIFY
    assert a["execution_branch"] == "execute/tb-science-rank18-20261010-v1"
    assert a["activation_filename"] == "ACTIVATE_RANK18_V1_PR.json"
    assert a["task_read"] is False
    assert a["task_started"] is False and a["benchmark_trials_consumed"] == 0
    assert a["task_read_authority"].startswith("ONLY_AFTER_EXACT_RANK18_V1_ACTIVATION_PR")

    l=load(s["ledger"]["path"])
    assert l["brain_ledger"]["git_blob_sha"] == BRAIN_LEDGER
    assert l["consumed_slots"] == 17
    assert l["rank18_task_read_history"] is False
    assert l["rank18_task_started"] is False
    assert l["rank18_benchmark_trials_consumed"] == 0

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for x in (e,c):
        assert x["slot_id"] == SLOT and x["task_digest"] == DIGEST
        assert x["execution_branch"] == "execute/tb-science-rank18-20261010-v1"
    assert c["activation_filename"] == "ACTIVATE_RANK18_V1_PR.json"
    assert c["lossless_raw_task_contract_git_blob_sha"] == RAW_BLOB
    assert c["explicit_requirement_index_git_blob_sha"] == INDEX_BLOB

    q=load("execution_guard/TB_SCIENCE_RANK15_CONSUMED_PUBLIC_QUARANTINE_V1.json")
    assert q["quarantine"]["rank15_replay_authority"] is False
    assert q["quarantine"]["rank15_replacement_authority"] is False

    print("PASS__TB_SCIENCE_RANK18_V1_ZERO_EXPOSURE_RESEAL__V12_ARTIFACT_FINISH_GATE_BOUND")

if __name__=="__main__":
    main()
