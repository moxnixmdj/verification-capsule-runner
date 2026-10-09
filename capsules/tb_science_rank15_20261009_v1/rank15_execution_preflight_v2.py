from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

C=Path(__file__).resolve().parent
SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V2"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
BRANCH="execute/tb-science-rank15-portable-20261009-v2"
ACT="ACTIVATE_RANK15_PORTABLE_V2_PR.json"
AUTH="52a5ccf4f44f40a84b6f2477e3e1f6859ac43bee"
AUTHV="937e4b398c6cd620618bd4327aec6b33bd7791aa"
LEDGER="6cbe4022917bd214d69a7596f3f90d5208c4ad66"
EPOCH="3ead70cc5c625b5523292de6f43446a836944a87"
CLAIM="f377aba4612ed86330c2de05d5adbec3aeb922c6"
AGENT="e7e258f567499bd7356c0276d6293aa30dbd338c"
PLANNER="58964dc8d6b5eed5c202081cd800035c791eeb1d"
POLICY="a525773417291c7a4841bf35e1baff5370350d0d"
GUARD="0139a20070cd1a51866c309bac1976b27ce7ac0d"

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name:str):
    return json.loads((C/name).read_text())

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation",action="store_true")
    args=ap.parse_args()
    errors=[]
    expected={
      "RANK15_EPOCH_V2.json":EPOCH,
      "RANK15_EXECUTION_CLAIM_V2.json":CLAIM,
      "rank15_prestart_token_guard_v1.py":GUARD,
      "canonical/runtime/harbor_science_agent_v1.py":AGENT,
      "canonical/runtime/harbor_science_planner_v1.py":PLANNER,
      "canonical/runtime/harbor_command_policy.py":POLICY,
    }
    for rel,exp in expected.items():
        p=C/rel
        if not p.is_file(): errors.append("MISSING:"+rel)
        elif blob(p)!=exp: errors.append("BLOB_MISMATCH:"+rel)
    try:
        e=load("RANK15_EPOCH_V2.json")
        c=load("RANK15_EXECUTION_CLAIM_V2.json")
        assert e["authority_blob"]==AUTH and e["authority_verification_blob"]==AUTHV
        assert e["ledger_blob"]==LEDGER and e["execution_branch"]==BRANCH
        assert e["predecessor_state"]["stale_pr_reuse_forbidden"] is True
        assert e["task_read_under_this_epoch"] is False and e["task_started"] is False
        assert e["benchmark_trials_executed"]==0
        assert c["authority_git_blob_sha"]==AUTH and c["authority_verification_git_blob_sha"]==AUTHV
        assert c["ledger_v20_git_blob_sha"]==LEDGER and c["epoch_v2_git_blob_sha"]==EPOCH
        assert c["execution_branch"]==BRANCH and c["activation_filename"]==ACT
        assert c["attempts_authorized"]==1 and c["retries_authorized"]==0
        assert c["replacement_allowed"] is False and c["precheck_failure_consumes_slot"] is False
        assert c["task_start_requires_prestart_token_budget_pass"] is True
        assert c["llama_binary_policy"]=="CLEAN_BUILD_ON_LIVE_RUNNER"
        assert c["stale_pr_2471_reuse_forbidden"] is True
        assert c["consumed"] is False and c["task_read_under_this_claim"] is False and c["task_started"] is False
    except Exception as exc:
        errors.append("STRUCTURAL:"+type(exc).__name__+":"+str(exc))
    active=(C/ACT).is_file()
    if args.require_activation:
        try:
            assert active
            a=load(ACT)
            assert a["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK15_PORTABLE_ACTIVATION_V2"
            assert a["activate"] is True and a["slot_id"]==SLOT and a["task_digest"]==DIGEST
            assert a["authority_git_blob_sha"]==AUTH and a["epoch_git_blob_sha"]==EPOCH
            assert a["execution_claim_git_blob_sha"]==CLAIM
            assert a["attempts_authorized"]==1 and a["retries_authorized"]==0
            assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
            assert os.environ.get("GITHUB_EVENT_NAME")=="pull_request"
            assert os.environ.get("GITHUB_BASE_REF")=="terminal-execution-v1"
            assert os.environ.get("GITHUB_HEAD_REF")==BRANCH
        except Exception as exc:
            errors.append("ACTIVATION:"+type(exc).__name__+":"+str(exc))
    elif active:
        errors.append("UNEXPECTED_ACTIVATION_DURING_STAGING")
    out={"schema":SCHEMA,"status":"PASS__RANK15_V2_PREFLIGHT__ZERO_TASK_EXPOSURE" if not errors else "FAIL_CLOSED","pass":not errors,"activation_present":active,"errors":errors,"task_read":False,"task_started":False,"benchmark_trials_consumed":0,"terminal_credit_delta":0}
    Path("RANK15_EXECUTION_PREFLIGHT_V2.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
