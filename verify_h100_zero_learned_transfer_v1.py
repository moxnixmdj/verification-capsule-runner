from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parent

EXPECTED={
    "canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json":"0aedbdff8520e5f1d274b490b274c756532ace4e",
    "canonical/governance/H100_ZERO_LEARNED_TRANSFER_CANDIDATE_V1.json":"7bc344c8e086aff6d7564e0b77f7d02cfc4a1d83",
    "canonical/runtime/h100_zero_learned_transfer_v1.py":"1bf0ebd74e9d413a9301031d33e619b397484e3c",
    "canonical/tests/test_h100_zero_learned_transfer_v1.py":"6213195d5c3487a9bde844a78291a76e25b0a29b",
    "canonical/runtime/h100_zero_learned_mechanism_synthesizer_v1.py":"fa77c6a0f4edf214c4237cf1e204b640261622fe",
    "canonical/runtime/h100_expression_tree_symbolic_regression_v1.py":"14e8f11c73e5fc0439016dbcd5b5a5a8d2c46490",
    "canonical/runtime/h100_zero_learned_parametric_unary_v1.py":"6a77f80e2cf01b079fcf7b688689d08a11b47c32",
}

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify_exact_blobs()->None:
    for rel,expected in EXPECTED.items():
        got=git_blob_sha((ROOT/rel).read_bytes())
        assert got==expected,(rel,got,expected)

def verify_transfer_result()->dict:
    out=transfer.run()
    assert out["persistent_learned_bytes"]==0,out
    assert out["external_frontier_model_calls"]==0,out
    assert out["external_learned_capability_calls"]==0,out
    assert out["family_count"]==3,out
    assert out["all_families_transfer_pass"] is True,out
    for family in out["families"]:
        b=family["transfer_task"]
        assert b["baseline"]["p_exact"]==0.0,(family["family_id"],b)
        assert b["post_compile"]["p_exact"]>0.0,(family["family_id"],b)
        assert b["post_compile"]["n95_proposals"] is not None,(family["family_id"],b)
        assert family["reuse_effect"]=="UNBOUNDED_TO_FINITE_T95",family
    return out

if __name__=="__main__":
    verify_exact_blobs()
    out=verify_transfer_result()
    compact={
        "status":out["status"],
        "all_families_transfer_pass":out["all_families_transfer_pass"],
        "persistent_learned_bytes":out["persistent_learned_bytes"],
        "families":[{
            "family_id":f["family_id"],
            "baseline_p":f["transfer_task"]["baseline"]["p_exact"],
            "post_compile_p":f["transfer_task"]["post_compile"]["p_exact"],
            "post_compile_n95":f["transfer_task"]["post_compile"]["n95_proposals"],
            "reuse_effect":f["reuse_effect"],
        } for f in out["families"]],
    }
    print(json.dumps(compact,indent=2,sort_keys=True))

# exact replay trigger; no semantic change
