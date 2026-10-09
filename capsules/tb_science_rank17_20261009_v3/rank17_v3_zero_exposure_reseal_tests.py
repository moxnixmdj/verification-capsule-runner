#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"capsules/tb_science_rank17_20261009_v3"
SLOT="terminal-bench-science/variable-star-vetting::trial-0"; DIGEST="sha256:51bf2b9d8e87a428772d92c6765d83ad3edc7c24283d2ff75af5f050aaee0c67"; WORKFLOW=".github/workflows/execute-tb-science-rank17-20261009-v3.yml"
def blob(rel):
    p=ROOT/rel; raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(rel): return json.loads((ROOT/rel).read_text())
def main():
    assert not (CAP/"ACTIVATE_RANK17_V3_PR.json").exists()
    s=load("execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    assert s["active"] is True and s["execution_authority"] is True and s["task_read_authority"] is True
    assert s["task_started"] is False and s["benchmark_trials_consumed"]==0
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST and s["workflow_path"]==WORKFLOW
    for k in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer"):
        assert blob(s[k]["path"])==s[k]["git_blob_sha"], k
    b=load(s["behavior"]["path"])
    assert b["runtime_bindings"]["agent"]["git_blob_sha"]=="124d13a7449281c9781c39df8f02c2e8f74226b4"
    assert "harbor_science_agent_v11.py" in b["runtime_bindings"]["agent"]["path"]
    assert "harbor_science_agent_v8.py" not in json.dumps(b)
    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"]=="f10ae44652cab95db1ad271ba6ae388aae137760"
    assert a["brain_ledger"]["git_blob_sha"]=="8f01d3f68664ca64ce727f69845b8db6eb9ce903"
    assert a["execution_branch"]=="execute/tb-science-rank17-20261009-v3" and a["activation_filename"]=="ACTIVATE_RANK17_V3_PR.json"
    l=load(s["ledger"]["path"]); assert l["rank17_task_read"] is False and l["rank17_task_started"] is False
    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for x in (e,c): assert x["slot_id"]==SLOT and x["task_digest"]==DIGEST and x["execution_branch"]=="execute/tb-science-rank17-20261009-v3"
    assert c["agent_v11_git_blob_sha"]=="124d13a7449281c9781c39df8f02c2e8f74226b4"
    assert "agent_v8_git_blob_sha" not in c
    q=load("execution_guard/TB_SCIENCE_RANK15_CONSUMED_PUBLIC_QUARANTINE_V1.json")
    assert q["quarantine"]["rank15_replay_authority"] is False and q["quarantine"]["rank15_replacement_authority"] is False
    print("PASS__TB_SCIENCE_RANK17_V1_ZERO_EXPOSURE_RESEAL")
if __name__=="__main__": main()
