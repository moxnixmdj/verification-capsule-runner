#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
from execution_guard.logical_attempt_identity_v2 import logical_attempt_identity

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/tb_science_rank21_20261011_v1"
SLOT="terminal-bench-science/ode-law-discovery::trial-0"
DIGEST="sha256:767d16a0a6226f391208b1b4bb126a6f957e5d0c8156342b5c9410a755142d65"
CLAIM_DIGEST="sha256:fb99e7f9d8d23a789c57506dc61e31c2abd25c442245f0309d94d65b29421697"
ATTEMPT="7eb619d40a65597b2b2dccbcf409c143aa47e1663ca4c0d8f098167cb252811a"
ACT=C/"ACTIVATE_RANK21_V1_PR.json"

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def canonical_sha256(v)->str:
    raw=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def main()->int:
    assert not ACT.exists(), "ACTIVATION_MUST_BE_ABSENT_DURING_RESEAL"
    claim=json.loads((C/"RANK21_LOGICAL_ATTEMPT_CLAIM_BINDING_V1.json").read_text())
    assert claim["slot_id"]==SLOT and claim["task_digest"]==DIGEST
    assert claim["task_read"] is False and claim["task_started"] is False
    assert claim["benchmark_trials_consumed"]==0
    assert canonical_sha256(claim)==CLAIM_DIGEST
    ident=logical_attempt_identity(slot_id=SLOT,task_digest=DIGEST,execution_claim_binding_digest=CLAIM_DIGEST)
    assert ident["logical_attempt_id"]==ATTEMPT

    new_paths=[
      "execution_guard/rank21_claim_bound_identity_v1.py",
      "capsules/tb_science_rank21_20261011_v1/rank21_execution_preflight_v8.py",
      "capsules/tb_science_rank21_20261011_v1/rank21_start_cas_v8.py",
      "capsules/tb_science_rank21_20261011_v1/rank21_prestart_token_guard_v5.py",
      "capsules/tb_science_rank21_20261011_v1/rank21_finalize_receipt_v7.py",
      "capsules/tb_science_rank21_20261011_v1/rank21_v8_status_journal_runner.py",
      ".github/workflows/execute-tb-science-rank21-20261011-v1.yml",
    ]
    forbidden=("terminal-bench-science/hysteretic-aquifer-control::trial-0",
               "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289")
    for rel in new_paths:
        text=(ROOT/rel).read_text(encoding="utf-8")
        assert all(x not in text for x in forbidden), "RANK20_SUBJECT_RESIDUE:"+rel

    surface_path=ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
    if surface_path.exists():
        surface=json.loads(surface_path.read_text())
        if surface.get("slot_id")==SLOT:
            assert surface["task_digest"]==DIGEST
            assert surface["task_read_history"] is False
            assert surface["task_started"] is False
            assert surface["benchmark_trials_consumed"]==0
            assert surface["activation_present"] is False
            assert surface["logical_attempt_id"]==ATTEMPT
            assert surface["execution_claim_binding_digest"]==CLAIM_DIGEST
            for key in ("behavior","authority","ledger","logical_attempt_claim_binding"):
                row=surface[key]
                assert blob(ROOT/row["path"])==row["git_blob_sha"], key
    print("PASS__RANK21_ZERO_EXPOSURE_RESEAL__CLAIM_BOUND__NO_ACTIVATION")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
