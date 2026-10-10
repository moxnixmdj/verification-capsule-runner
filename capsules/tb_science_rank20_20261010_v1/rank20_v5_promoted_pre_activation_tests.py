#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SURFACE="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT="terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST="sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
ATTEMPT="c7a02ecc6b11f4338120f05cd922370d361ce79e104549f95b656df3b51cb2bb"
CLAIM_DIGEST="sha256:aa0d91d18bb597319414b7385a92248992c093e14bf9c8f5677b72c05cb09beb"
AUTH="7b974adda057c2d5a6d31cb0587a0b2728819c8e"
LEDGER="fbd93a78afdcca1e926ced19e6cc32f5b6cd2ef6"
EPOCH="0ed240c0d49b574d1d23010fc01502b7a323bfa2"
CLAIM="fd3244c58e9185adda76284abf36c9ee54095965"
BEHAVIOR="8c3d285161f356c9256375c9168e88cdaadd58e5"
CLAIM_BINDING="7d94ac0b86053a31fd711dcb0652370041671e44"
REFINEMENT="71143dd544ea956e7d4a535eb16c9a863793481f"
BRAIN_AUTH="d50b123ed0df77fbd772e00331f278835d4bf35b"
BRAIN_LEDGER="2d8c04e85b4d611b2074a6fdcab71c031febe284"

def load(rel):
    x=json.loads((ROOT/rel).read_text())
    assert isinstance(x,dict), rel
    return x
def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def bound(row):
    assert isinstance(row,dict)
    assert blob(row["path"])==row["git_blob_sha"]
    return row["path"]
def main():
    s=load(SURFACE)
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["logical_attempt_id"]==ATTEMPT
    assert s["execution_claim_binding_digest"]==CLAIM_DIGEST
    assert s["execution_authority"] is True and s["task_read_authority"] is True
    assert s["task_read_history"] is False and s["task_started"] is False
    assert s["benchmark_trials_consumed"]==0
    assert not (ROOT/s["activation_path"]).exists()
    for k in ("behavior","authority","ledger","invariant_registry","admission_guard","logical_attempt_claim_binding","epoch","execution_claim","preflight","finalizer","behavior_refinement_verification"):
        bound(s[k])
    assert s["authority"]["git_blob_sha"]==AUTH
    assert s["ledger"]["git_blob_sha"]==LEDGER
    assert s["epoch"]["git_blob_sha"]==EPOCH
    assert s["execution_claim"]["git_blob_sha"]==CLAIM
    assert s["behavior"]["git_blob_sha"]==BEHAVIOR
    assert s["logical_attempt_claim_binding"]["git_blob_sha"]==CLAIM_BINDING
    assert s["behavior_refinement_verification"]["git_blob_sha"]==REFINEMENT
    a=load(s["authority"]["path"]); l=load(s["ledger"]["path"])
    assert a["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_AUTHORITY_BINDING_V6"
    assert a["brain_authority"]["git_blob_sha"]==BRAIN_AUTH
    assert a["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER
    assert a["execution_authority"] is True and a["task_read_authority"] is True
    assert a["activation_authority"] is False
    assert l["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_LEDGER_BINDING_V48"
    assert l["brain_authority"]["git_blob_sha"]==BRAIN_AUTH
    assert l["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER
    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for d in (e,c):
        assert d["logical_attempt_id"]==ATTEMPT
        assert d["execution_claim_binding_digest"]==CLAIM_DIGEST
        assert d["execution_authority"] is True
        assert d["execution_authority_effective"] is True
        assert d["task_read_authority"] is True
        assert d["activation_present"] is False
    subprocess.check_call([sys.executable,str(ROOT/s["behavior_refinement_verification"]["path"])])
    print("PASS__RANK20_V5_PROMOTED_EFFECTIVE_AUTHORITY__PREACTIVATION__ZERO_EXPOSURE")
    return 0
if __name__=="__main__": raise SystemExit(main())
