#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OLD="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V6.json"
NEW="execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V7.json"
CLAIM="capsules/tb_science_rank20_20261010_v1/RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_V11.json"
CLAIM_SHA="5bcded2e52f971f3e5c63c7e15ac65cffe892d9d"
def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(rel): return json.loads((ROOT/rel).read_text())
def main():
    old,new=load(OLD),load(NEW)
    assert old["slot_id"]==new["slot_id"] and old["task_digest"]==new["task_digest"]
    assert old["scope"]==new["scope"] and old["behavior"]==new["behavior"]
    for k,v in old["runtime_bindings"].items():
        assert new["runtime_bindings"].get(k)==v,k
    row=new["runtime_bindings"].get("logical_attempt_claim_binding")
    assert row=={"path":CLAIM,"git_blob_sha":CLAIM_SHA},row
    assert blob(CLAIM)==CLAIM_SHA
    assert new["task_read"] is False and new["task_started"] is False
    assert new["benchmark_trials_executed"]==0 and new["execution_authority"] is False
    print("PASS__RANK20_V7_PREVIOUS_CLAIM_BINDING_STRICT_REFINEMENT__ZERO_EXPOSURE")
    return 0
if __name__=="__main__": raise SystemExit(main())
