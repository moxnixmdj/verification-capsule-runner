#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SURFACE="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT="terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST="sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
ATTEMPT="c7a02ecc6b11f4338120f05cd922370d361ce79e104549f95b656df3b51cb2bb"
CLAIM_DIGEST="sha256:aa0d91d18bb597319414b7385a92248992c093e14bf9c8f5677b72c05cb09beb"
AUTH_BLOB="ed796d6bb51e14fcacdea9222124897321856ef8"
LEDGER_BLOB="317b6997344d8fa588a20a73b3c7978bae2f2616"
EPOCH_BLOB="e7446cbc8ef2b655a51fc59134dff12d6161052e"
CLAIM_BLOB="5f3deca2d53910dba1622ec1e23d3b45e47af2b1"
BRAIN_AUTH_BLOB="d50b123ed0df77fbd772e00331f278835d4bf35b"
BRAIN_LEDGER_BLOB="2d8c04e85b4d611b2074a6fdcab71c031febe284"
CLAIM_BINDING_BLOB="7d94ac0b86053a31fd711dcb0652370041671e44"
WORKFLOW_BLOB="e4cb372e501790fd9ed5aa72193d18109a599102"
BEHAVIOR_BLOB="8c3d285161f356c9256375c9168e88cdaadd58e5"
REFINEMENT_BLOB="71143dd544ea956e7d4a535eb16c9a863793481f"

def load(rel:str)->dict[str,Any]:
    x=json.loads((ROOT/rel).read_text())
    assert isinstance(x,dict),rel
    return x

def blob(rel:str)->str:
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def bind(row:Any,label:str)->str:
    assert isinstance(row,Mapping),(label,row)
    rel=row.get("path"); sha=row.get("git_blob_sha")
    assert isinstance(rel,str) and isinstance(sha,str),(label,row)
    assert (ROOT/rel).is_file(),(label,rel)
    assert blob(rel)==sha,(label,rel,blob(rel),sha)
    return rel

def main()->int:
    s=load(SURFACE)
    assert s["schema"]=="PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1"
    assert s["family"]=="TB_SCIENCE" and s["active"] is True
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["logical_attempt_id"]==ATTEMPT
    assert s["execution_claim_binding_digest"]==CLAIM_DIGEST
    assert s["execution_authority"] is True and s["task_read_authority"] is True
    assert s["task_read_history"] is False and s["task_started"] is False
    assert s["benchmark_trials_consumed"]==0 and s["terminal_credit_delta"]==0
    assert not (ROOT/s["activation_path"]).exists()
    for key in ("behavior","authority","ledger","invariant_registry","admission_guard","epoch","execution_claim","preflight","finalizer","logical_attempt_claim_binding","behavior_refinement_verification"):
        bind(s[key],"surface."+key)
    assert s["authority"]["git_blob_sha"]==AUTH_BLOB
    assert s["ledger"]["git_blob_sha"]==LEDGER_BLOB
    assert s["epoch"]["git_blob_sha"]==EPOCH_BLOB
    assert s["execution_claim"]["git_blob_sha"]==CLAIM_BLOB
    assert s["behavior"]["git_blob_sha"]==BEHAVIOR_BLOB
    assert s["workflow_git_blob_sha"]==WORKFLOW_BLOB
    assert s["logical_attempt_claim_binding"]["git_blob_sha"]==CLAIM_BINDING_BLOB
    assert s["behavior_refinement_verification"]["git_blob_sha"]==REFINEMENT_BLOB

    a=load(s["authority"]["path"])
    assert a["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_AUTHORITY_BINDING_V6"
    assert a["brain_authority"]["git_blob_sha"]==BRAIN_AUTH_BLOB
    assert a["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER_BLOB
    assert a["ledger"]["git_blob_sha"]==LEDGER_BLOB
    assert a["execution_authority"] is True and a["task_read_authority"] is True
    assert a["activation_authority"] is False and a["task_read_history"] is False
    assert a["task_started"] is False and a["benchmark_trials_consumed"]==0

    l=load(s["ledger"]["path"])
    assert l["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK20_PUBLIC_LEDGER_BINDING_V48"
    assert l["brain_authority"]["git_blob_sha"]==BRAIN_AUTH_BLOB
    assert l["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER_BLOB
    assert l["logical_attempt_id"]==ATTEMPT
    assert l["execution_claim_binding_digest"]==CLAIM_DIGEST
    assert l["rank20_task_read_history"] is False and l["rank20_task_started"] is False
    assert l["rank20_start_cas_acquired"] is False and l["rank20_benchmark_trials_consumed"]==0
    assert l["activation_present"] is False

    e=load(s["epoch"]["path"]); c=load(s["execution_claim"]["path"])
    for doc in (e,c):
        assert doc["slot_id"]==SLOT and doc["task_digest"]==DIGEST
        assert doc["logical_attempt_id"]==ATTEMPT
        assert doc["execution_claim_binding_digest"]==CLAIM_DIGEST
        assert doc["brain_authority_blob"]==BRAIN_AUTH_BLOB
        assert doc["brain_ledger_blob"]==BRAIN_LEDGER_BLOB
        assert doc["execution_authority"] is True and doc["execution_authority_effective"] is True
        assert doc["task_read_authority"] is True and doc["activation_present"] is False
    assert e["public_authority_binding_blob"]==AUTH_BLOB and e["public_ledger_binding_blob"]==LEDGER_BLOB
    assert c["public_authority_binding_blob"]==AUTH_BLOB and c["public_ledger_binding_blob"]==LEDGER_BLOB
    assert c["epoch_git_blob_sha"]==EPOCH_BLOB

    env=dict(os.environ); env["PYTHONPATH"]=str(ROOT)+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    subprocess.check_call([sys.executable,str(ROOT/s["behavior_refinement_verification"]["path"])],cwd=ROOT,env=env)
    subprocess.check_call([sys.executable,str(ROOT/"capsules/tb_science_rank20_20261010_v1/rank20_v2_zero_exposure_reseal_tests.py")],cwd=ROOT,env=env)
    print("PASS__RANK20_V5_PROMOTED_EFFECTIVE_AUTHORITY__PREACTIVATION__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
