#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"capsules/tb_science_rank18_20261010_v1"
RUNTIME=ROOT/"capsules/tb_science_rank15_20261009_v1"
SLOT="terminal-bench-science/longitudinal-clinical-agent::trial-0"
DIGEST="sha256:e9a166b2173f7014d4f1559505397b221f94bc446eab031f94791b35e0e5f1c9"
WORKFLOW=".github/workflows/execute-tb-science-rank18-20261010-v1.yml"
BRAIN_AUTHORITY_V3="7ab3d1d294d82192462c735ff7cb7e0dc3abc06f"
BRAIN_LEDGER_V35="73ad3e6e2b9cb9e1f3b72c3f08d6842814ca1940"
BRAIN_ABORT_TRUTH="fd53eecbf4d974e45c936d592005f5f7d518e87d"
BRAIN_REPAIR_VERIFY="aec85d3a6b82aa8ab7a6942b535838333195fb9c"
RUNNER_BLOB="d1bb9fc6766f16b34a955c6f1b41d2da0b2709df"

def blob(rel):
    p=ROOT/rel; raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def verify_bridge():
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    if str(RUNTIME) not in sys.path: sys.path.insert(0,str(RUNTIME))
    if str(CAP) not in sys.path: sys.path.insert(0,str(CAP))
    import rank18_v6_status_journal_runner as r
    assert r._artifact_source_for_agent("/app/legacy.json")=="/app/legacy.json"
    assert r._artifact_source_for_agent({"source":"/root/results/trajectory.json","service":"main"})=="/root/results/trajectory.json"
    assert r._artifact_source_for_agent({"source":"/var/log/clinenv/actions.jsonl","service":"broker"}) is None
    try:
        r._artifact_source_for_agent({"source":"../escape.json","service":"main"})
    except r.BarrierRunnerError as exc:
        assert str(exc)=="TASK_ARTIFACT_SOURCE_INVALID"
    else:
        raise AssertionError("traversal must fail closed")

def main():
    assert not (CAP/"ACTIVATE_RANK18_V1_PR.json").exists()
    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["active"] is True
    assert s["execution_authority"] is True
    assert s["task_read_authority"] is True
    assert s["task_read_history"] is True
    assert s["task_started"] is False
    assert s["benchmark_trials_consumed"]==0
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["workflow_path"]==WORKFLOW

    for key in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer"):
        assert blob(s[key]["path"])==s[key]["git_blob_sha"], key
    assert blob(WORKFLOW)==s["workflow_git_blob_sha"]

    b=load(s["behavior"]["path"])
    rb=b["runtime_bindings"]
    assert rb["status_journal_runner"]["git_blob_sha"]==RUNNER_BLOB
    assert blob(rb["status_journal_runner"]["path"])==RUNNER_BLOB
    assert b["behavior"]["harbor_artifact_config_string_and_table_forms_supported"] is True
    assert b["behavior"]["main_service_artifact_source_paths_injected_as_agent_deliverables"] is True
    assert b["behavior"]["sidecar_service_artifacts_not_misclassified_as_agent_deliverables"] is True

    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"]==BRAIN_AUTHORITY_V3
    assert a["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER_V35
    assert a["brain_prestart_abort_truth"]["git_blob_sha"]==BRAIN_ABORT_TRUTH
    assert a["brain_artifact_config_bridge_repair_verification"]["git_blob_sha"]==BRAIN_REPAIR_VERIFY
    assert a["task_read_history"] is True
    assert a["task_started"] is False and a["benchmark_trials_consumed"]==0

    l=load(s["ledger"]["path"])
    assert l["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER_V35
    assert l["consumed_slots"]==17
    assert l["rank18_task_read_history"] is True
    assert l["rank18_task_started"] is False
    assert l["rank18_benchmark_trials_consumed"]==0

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for x in (e,c):
        assert x["slot_id"]==SLOT and x["task_digest"]==DIGEST
        assert x["execution_branch"]=="execute/tb-science-rank18-20261010-v1"
    assert e["task_read_history_before_epoch"] is True
    assert c["task_read_history_before_claim"] is True

    verify_bridge()
    print("PASS__TB_SCIENCE_RANK18_V2_ZERO_EXPOSURE_RESEAL__ARTIFACTCONFIG_BRIDGE__TASK_READ_HISTORY_BOUND")

if __name__=="__main__":
    main()
