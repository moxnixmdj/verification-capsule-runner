from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

C=Path(__file__).resolve().parent
ROOT=C.parents[1]
SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V2"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
BRANCH="execute/tb-science-rank15-20261009-v2"
ACT="ACTIVATE_RANK15_V2_PR.json"
AUTH_BLOB="a3907605eeb818a9e89d5ecbba02991601fd53c0"
BRAIN_AUTH="a292a898231973204f66bf92c3f70ce2bf422449"
EPOCH_BLOB="2653e53826dceab82a3717148965f025dd69478a"
CLAIM_BLOB="ac0db733ddfbbcc71a314bfdf1d024dd06bef7f8"

def git_blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path:Path):
    x=json.loads(path.read_text())
    if not isinstance(x,dict): raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return x

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation",action="store_true")
    args=ap.parse_args()
    errors=[]
    expected={
      "TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json":AUTH_BLOB,
      "RANK15_EPOCH_V2.json":EPOCH_BLOB,
      "RANK15_EXECUTION_CLAIM_V2.json":CLAIM_BLOB,
      "canonical/runtime/harbor_science_agent_v2.py":"fb4d8202192ca7a7ff03b36b9ba31be48f19dfa4",
      "canonical/runtime/harbor_science_planner_v2.py":"92161f95f211377ed40c11a38e641046bb45bd26",
      "rank15_prestart_token_guard_v2.py":"b296e442535d4cf7770f7c1464da441c80fc65a1",
      "canonical/runtime/harbor_environment_transport.py":"ec46f648214a37bb16025d5ef2593efdf59f0d79",
    }
    for rel,sha in expected.items():
        p=C/rel
        if not p.is_file(): errors.append("MISSING:"+rel)
        elif git_blob(p)!=sha: errors.append("BLOB_MISMATCH:"+rel)
    try:
        a=load(C/"TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json")
        e=load(C/"RANK15_EPOCH_V2.json")
        q=load(C/"RANK15_EXECUTION_CLAIM_V2.json")
        s=load(ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
        assert a["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK15_PUBLIC_AUTHORITY_BINDING_V3"
        assert a["brain_authority_git_blob_sha"]==BRAIN_AUTH
        assert a["execution_authority"] is True and a["task_read_authority"] is False
        assert a["task_read"] is False and a["task_started"] is False and a["benchmark_trials_consumed"]==0
        assert e["public_authority_binding_git_blob_sha"]==AUTH_BLOB
        assert e["execution_branch"]==BRANCH and e["activation_filename"]==ACT
        assert e["run_attempts_authorized_by_epoch"]==0
        assert e["task_read"] is False and e["task_started"] is False and e["benchmark_trials_consumed"]==0
        assert q["public_authority_binding_git_blob_sha"]==AUTH_BLOB
        assert q["epoch_v2_git_blob_sha"]==EPOCH_BLOB
        assert q["execution_branch"]==BRANCH and q["activation_filename"]==ACT
        assert q["attempts_authorized"]==1 and q["retries_authorized"]==0 and q["replacement_allowed"] is False
        assert q["precheck_failure_consumes_slot"] is False and q["post_start_result_is_irreversible"] is True
        assert q["consumed"] is False and q["task_read"] is False and q["task_started"] is False
        assert s["workflow_path"]==".github/workflows/execute-tb-science-rank15-20261009-v2.yml"
        assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
        assert s["execution_authority"] is True
        assert s["authority"]["path"]=="capsules/tb_science_rank15_20261009_v1/TB_SCIENCE_RANK15_ONE_SLOT_EXECUTION_AUTHORITY_20261009_V1.json"
        assert s["authority"]["git_blob_sha"]==AUTH_BLOB
    except Exception as exc:
        errors.append("STRUCTURAL:"+type(exc).__name__+":"+str(exc))
    active=(C/ACT).is_file()
    if args.require_activation:
        try:
            assert active
            x=load(C/ACT)
            assert x["schema"]=="PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V2"
            assert x["activate"] is True and x["slot_id"]==SLOT and x["task_digest"]==DIGEST
            assert x["public_authority_binding_git_blob_sha"]==AUTH_BLOB
            assert x["brain_authority_git_blob_sha"]==BRAIN_AUTH
            assert x["epoch_v2_git_blob_sha"]==EPOCH_BLOB and x["execution_claim_v2_git_blob_sha"]==CLAIM_BLOB
            assert x["attempts_authorized"]==1 and x["retries_authorized"]==0 and x["replacement_allowed"] is False
            assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
            assert os.environ.get("GITHUB_EVENT_NAME")=="pull_request"
            assert os.environ.get("GITHUB_BASE_REF")=="terminal-execution-v1"
            assert os.environ.get("GITHUB_HEAD_REF")==BRANCH
        except Exception as exc:
            errors.append("ACTIVATION:"+type(exc).__name__+":"+str(exc))
    elif active:
        errors.append("UNEXPECTED_ACTIVATION_DURING_STAGING")
    out={
      "schema":SCHEMA,
      "status":"PASS__RANK15_V2_EXACT_AUTHORITY_EPOCH_CLAIM_PREFLIGHT__ZERO_TASK_EXPOSURE" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "activation_present":active,
      "errors":errors,
      "task_read":False,
      "task_started":False,
      "benchmark_trials_consumed":0,
      "terminal_credit_delta":0
    }
    (ROOT/"RANK15_EXECUTION_PREFLIGHT_V2.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
