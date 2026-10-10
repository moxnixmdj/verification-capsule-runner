#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V5.json"
NEW="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V6.json"
TEST="capsules/tb_science_rank20_20261010_v1/rank20_v3_zero_exposure_reseal_tests.py"
GEN="execution_guard/tests/test_rank20_v8_generation_neutral_gate_v1.py"
EXPECTED_TEST="b8947edc9a5c1ab8dad92ee6156bafa73dada14c"
EXPECTED_GEN="c861fd98542ab91177cc1eeba72feae675056353"

def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    value=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    assert isinstance(value,dict)
    return value

def main():
    old=load(OLD); new=load(NEW)
    assert old["slot_id"]==new["slot_id"]
    assert old["task_digest"]==new["task_digest"]
    assert old["workflow_path"]==new["workflow_path"]
    assert old["behavior"]==new["behavior"]
    changed={k for k in old["runtime_bindings"] if old["runtime_bindings"][k]!=new["runtime_bindings"][k]}
    assert changed=={"zero_exposure_tests"}, changed
    z=new["runtime_bindings"]["zero_exposure_tests"]
    assert z["path"]==TEST and z["git_blob_sha"]==EXPECTED_TEST
    assert blob(TEST)==EXPECTED_TEST
    assert blob(GEN)==EXPECTED_GEN
    text=(ROOT/TEST).read_text(encoding="utf-8")
    assert "execute/tb-science-rank20-20261010-v3" in text
    assert "ACTIVATE_RANK20_V3_PR.json" in text
    assert "execute/tb-science-rank20-20261010-v2" not in text
    assert "ACTIVATE_RANK20_V2_PR.json" not in text
    subprocess.check_call([sys.executable,str(ROOT/GEN)],cwd=ROOT)
    assert new["task_read"] is False
    assert new["task_started"] is False
    assert new["benchmark_trials_executed"]==0
    print("PASS__RANK20_V6_V3_ZERO_EXPOSURE_HARNESS_REFINEMENT")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
