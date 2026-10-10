#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
NEW="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V5.json"
WORKFLOW=".github/workflows/execute-tb-science-rank20-20261010-v1.yml"
CAS="capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v8.py"
PREFLIGHT="capsules/tb_science_rank20_20261010_v1/rank20_execution_preflight_v8.py"
ZERO="capsules/tb_science_rank20_20261010_v1/rank20_v2_zero_exposure_reseal_tests.py"
GATE_TEST="execution_guard/tests/test_rank20_v8_generation_neutral_gate_v1.py"

EXPECTED={
 WORKFLOW:"344dcef48c7ae176aa0851c7e8e80bc80579868e",
 CAS:"99d81c7d1316d1767c688e12c2c05790c69662f3",
 PREFLIGHT:"3cc62699388993a053969b03d09343c0e8a4d659",
 ZERO:"72811ee9fe7adcd9e4223c731a78651c50fb28df",
 GATE_TEST:"c861fd98542ab91177cc1eeba72feae675056353",
}

def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel):
    x=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    assert isinstance(x,dict)
    return x

def main():
    old,new=load(OLD),load(NEW)
    assert old["slot_id"]==new["slot_id"]
    assert old["task_digest"]==new["task_digest"]
    assert old["scope"]==new["scope"]
    for k,v in old["behavior"].items():
        assert new["behavior"].get(k)==v, ("behavior_regression",k)
    for k in (
        "generation_neutral_inner_activation_gate",
        "outer_workflow_fresh_v3_activation_trigger",
        "outer_workflow_fresh_v3_head_and_diff_gate",
        "workflow_invokes_generation_neutral_preflight_v8",
        "workflow_invokes_generation_neutral_start_cas_v8",
    ):
        assert new["behavior"].get(k) is True, k
    for rel,sha in EXPECTED.items():
        assert blob(rel)==sha, rel
    assert new["runtime_bindings"]["start_cas"]["path"]==CAS
    assert new["runtime_bindings"]["start_cas"]["git_blob_sha"]==EXPECTED[CAS]
    assert new["runtime_bindings"]["preflight"]["path"]==PREFLIGHT
    assert new["runtime_bindings"]["preflight"]["git_blob_sha"]==EXPECTED[PREFLIGHT]
    assert new["runtime_bindings"]["zero_exposure_tests"]["path"]==ZERO
    assert new["runtime_bindings"]["zero_exposure_tests"]["git_blob_sha"]==EXPECTED[ZERO]
    assert "logical_attempt_claim_binding" not in new["runtime_bindings"]
    wf=(ROOT/WORKFLOW).read_text(encoding="utf-8")
    for retired in ("execute/tb-science-rank20-20261010-v2","ACTIVATE_RANK20_V2_PR.json"):
        assert retired not in wf
    for required in ("execute/tb-science-rank20-20261010-v3","ACTIVATE_RANK20_V3_PR.json","rank20_execution_preflight_v8.py","rank20_start_cas_v8.py"):
        assert required in wf
    assert new["task_read"] is False and new["task_started"] is False
    assert new["benchmark_trials_executed"]==0
    assert new["execution_authority"] is False
    print("PASS__RANK20_V5_GENERATION_NEUTRAL_CARRIER_STRICT_REFINEMENT__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
