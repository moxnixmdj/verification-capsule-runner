#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"capsules/tb_science_rank16_20261009_v1"
SLOT="terminal-bench-science/sparse-network-assimilation::trial-0"; DIGEST="sha256:52ba7089dc32952df08c478af76b732fa82468c125431388adbf9798d869826f"; WORKFLOW=".github/workflows/execute-tb-science-rank16-20261009-v1.yml"
def blob(rel):
    p=ROOT/rel; raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(rel): return json.loads((ROOT/rel).read_text())
def main():
    assert not (CAP/"ACTIVATE_RANK16_V1_PR.json").exists()
    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["active"] is True and s["execution_authority"] is True and s["task_read_authority"] is True
    assert s["task_started"] is False and s["benchmark_trials_consumed"]==0
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST and s["workflow_path"]==WORKFLOW
    for k in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer"):
        assert blob(s[k]["path"])==s[k]["git_blob_sha"], k
    b=load(s["behavior"]["path"])
    assert b["runtime_bindings"]["agent"]["git_blob_sha"]=="c3b9bbc93e070b9974598636ebbb2fd3156581cb"
    assert "harbor_science_agent_v9.py" in b["runtime_bindings"]["agent"]["path"]
    assert "harbor_science_agent_v8.py" not in json.dumps(b)
    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"]=="20ebbe8ed593a7ead08b27a1c57864ede429cb46"
    assert a["brain_ledger"]["git_blob_sha"]=="7e46f2a5c0c418a4d3be4360c8a85b7be7611abb"
    assert a["execution_branch"]=="execute/tb-science-rank16-20261009-v1" and a["activation_filename"]=="ACTIVATE_RANK16_V1_PR.json"
    l=load(s["ledger"]["path"]); assert l["rank16_task_read"] is False and l["rank16_task_started"] is False
    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for x in (e,c): assert x["slot_id"]==SLOT and x["task_digest"]==DIGEST and x["execution_branch"]=="execute/tb-science-rank16-20261009-v1"
    assert c["agent_v9_git_blob_sha"]=="c3b9bbc93e070b9974598636ebbb2fd3156581cb"
    assert "agent_v8_git_blob_sha" not in c
    q=load("execution_guard/TB_SCIENCE_RANK15_CONSUMED_PUBLIC_QUARANTINE_V1.json")
    assert q["quarantine"]["rank15_replay_authority"] is False and q["quarantine"]["rank15_replacement_authority"] is False
    print("PASS__TB_SCIENCE_RANK16_V1_ZERO_EXPOSURE_RESEAL")
if __name__=="__main__": main()
