#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, urllib.request, zipfile, io

REPO="moxnixmdj/verification-capsule-runner"
RUN_ID=37191933717
JOB_ID=111405786415
HEAD_SHA="ad616add68ea21dd0e13505f3490638fa01e6cc7"
RECEIPT=pathlib.Path("subject/livebench_v6_replay72_truth_20261004/receipt.json")
EXPECTED_RECEIPT_BLOB="fee64ba81fbee1117db48eb406a2ea11cc7ff9fb"

def git_blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def get(url):
    token=os.environ.get("GITHUB_TOKEN","")
    req=urllib.request.Request(url,headers={
      "Accept":"application/vnd.github+json",
      "Authorization":"Bearer "+token,
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"brain-independent-verifier",
    })
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read(), r.headers.get("Content-Type","")

def main():
    if git_blob_sha(RECEIPT)!=EXPECTED_RECEIPT_BLOB:
        raise SystemExit("RECEIPT_BLOB_MISMATCH")
    receipt=json.loads(RECEIPT.read_text())
    raw,_=get(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}")
    run=json.loads(raw)
    if run.get("status")!="completed" or run.get("conclusion")!="success":
        raise SystemExit("RUN_NOT_SUCCESS")
    if run.get("head_sha")!=HEAD_SHA:
        raise SystemExit("RUN_HEAD_MISMATCH")

    raw,ctype=get(f"https://api.github.com/repos/{REPO}/actions/jobs/{JOB_ID}/logs")
    # GitHub currently returns decoded text for one job; tolerate zip defensively.
    if raw[:2]==b"PK":
        z=zipfile.ZipFile(io.BytesIO(raw))
        log="\n".join(z.read(n).decode("utf-8","replace") for n in z.namelist())
    else:
        log=raw.decode("utf-8","replace")

    pre=[x.split("LIVEBENCH_V6_PRELAUNCH=",1)[1] for x in log.splitlines() if "LIVEBENCH_V6_PRELAUNCH=" in x]
    cases=[x.split("LIVEBENCH_CASE_RECEIPT=",1)[1] for x in log.splitlines() if "LIVEBENCH_CASE_RECEIPT=" in x]
    term=[x.split("LIVEBENCH_TERMINAL_RESULT=",1)[1] for x in log.splitlines() if "LIVEBENCH_TERMINAL_RESULT=" in x]
    if len(pre)!=1 or len(cases)!=72 or len(term)!=1:
        raise SystemExit(f"LOG_CARDINALITY:{len(pre)}:{len(cases)}:{len(term)}")
    p=json.loads(pre[0]); cs=[json.loads(x) for x in cases]; t=json.loads(term[0])

    policy=sum(1 for x in cs if x.get("inference_error")=="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION")
    exits=sum(1 for x in cs if str(x.get("inference_error") or "").startswith("INFERENCE_EXIT_1:"))
    valid=sum(1 for x in cs if not x.get("inference_error"))
    scoring=sum(1 for x in cs if x.get("scoring_error"))

    obs=receipt["observed"]; scope=receipt["scope"]; ex=receipt["execution"]
    checks=[
      p.get("compatible") is True,
      p.get("new_case_exposure_authorized") is False,
      p.get("point_of_use_root_git_blob_sha")==ex["point_of_use_root_git_blob_sha"],
      len(cs)==scope["terminal_cases_consumed"]==72,
      valid==obs["valid_candidate_responses"]==0,
      policy==obs["policy_blocked_post_prompt_capability_acquisition"]==43,
      exits==obs["inference_exit_nonzero"]==29,
      scoring==obs["scoring_errors"]==0,
      t.get("status")=="FAIL_FORCED",
      t.get("predicate_fail_forced") is True,
      t.get("predicate_pass_forced") is False,
      t.get("observed_score_mass")==obs["observed_score_mass"]==0,
      t.get("conservative_full_population_upper_percent")==obs["conservative_full_population_upper_percent"]==64.0,
      t.get("threshold_percent")==obs["threshold_percent"]==65.7,
      t.get("receipts_sha256")==obs["receipts_sha256"]=="2f7ab71c76ac27228b6dc57784b72fa8ea4e4032c12b0d7301a1d9ec851333b1",
      t.get("incremental_spend_usd")==0,
      t.get("paid_external_model_or_api_used") is False,
      receipt["interpretation"]["capability_level_result"]=="NOT_ESTABLISHED",
      receipt["interpretation"]["root1_reopen_authorized"] is False,
      receipt.get("execution_authority") is False,
      receipt.get("fresh_reality_authority") is False,
      receipt.get("promotion_authority") is False,
    ]
    if not all(checks):
        raise SystemExit("TRUTH_RECEIPT_MISMATCH")
    out={
      "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__LIVEBENCH_V6_REPLAY72_DIAGNOSTIC_TRUTH__ZERO_CREDIT",
      "receipt_git_blob_sha":EXPECTED_RECEIPT_BLOB,
      "workflow_run_id":RUN_ID,
      "workflow_job_id":JOB_ID,
      "terminal_cases_replayed":72,
      "new_terminal_cases_consumed":0,
      "valid_candidate_responses":valid,
      "policy_blocked":policy,
      "inference_exit_nonzero":exits,
      "score_mass":t.get("observed_score_mass"),
      "full_population_upper_percent":t.get("conservative_full_population_upper_percent"),
      "threshold_percent":t.get("threshold_percent"),
      "route_fail_forced":True,
      "capability_failure_proved":False,
      "root1_reopen_authorized":False,
      "acceptance_credit_delta":0,
      "incremental_spend_usd":0
    }
    print(json.dumps(out,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
