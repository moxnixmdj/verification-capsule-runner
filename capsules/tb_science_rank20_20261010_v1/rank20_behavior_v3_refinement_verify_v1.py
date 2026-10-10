#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SEED="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V2.json"
EFFECTIVE="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V3.json"
ACTIVATION="capsules/tb_science_rank20_20261010_v1/ACTIVATE_RANK20_V2_PR.json"

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def main():
    a=load(SEED); b=load(EFFECTIVE)
    assert a["slot_id"]==b["slot_id"]=="terminal-bench-science/hysteretic-aquifer-control::trial-0"
    assert a["task_digest"]==b["task_digest"]=="sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
    assert a["scope"]==b["scope"]
    assert a["workflow_path"]==b["workflow_path"]==".github/workflows/execute-tb-science-rank20-20261010-v1.yml"
    assert a["behavior"]==b["behavior"]

    changed={"preflight","start_cas","zero_exposure_tests"}
    assert set(a["runtime_bindings"])==set(b["runtime_bindings"])
    for key in a["runtime_bindings"]:
        if key in changed:
            continue
        assert a["runtime_bindings"][key]==b["runtime_bindings"][key], key

    expected={
      "preflight":("27d6834cc4028f922c57da332a7ee3b2b0959338","74d55719d01f3f434b0b75001548f56a4ed83ff6"),
      "start_cas":("344cf19146f722b22cc1d14d58a096b3b1e1ad2d","35cd4c7a31d5ffbafa755dcdf888c2dee1beeb1b"),
      "zero_exposure_tests":("b93af6baee042ac09f352b1a12c84fc03123c55d","ba2d467c54a9f9720bc1b647befe655b80555fab"),
    }
    for key,(old,new) in expected.items():
        assert a["runtime_bindings"][key]["git_blob_sha"]==old
        assert b["runtime_bindings"][key]["git_blob_sha"]==new
        assert blob(b["runtime_bindings"][key]["path"])==new

    assert a["task_read"] is False and b["task_read"] is False
    assert a["task_started"] is False and b["task_started"] is False
    assert a["benchmark_trials_executed"]==b["benchmark_trials_executed"]==0
    assert a["execution_authority"] is True
    assert b["execution_authority"] is False
    assert b["promotion_authority"] is False
    assert b["acceptance_credit_delta"]==0
    assert b["terminal_credit_delta"]==0
    assert not (ROOT/ACTIVATION).exists()
    print("PASS__RANK20_V3_EFFECTIVE_BEHAVIOR_REFINEMENT__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
