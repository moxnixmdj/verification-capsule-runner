#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, sys, urllib.request

REPO="moxnixmdj/verification-capsule-runner"
RUN_ID=37191977679
JOB_ID=111405917591
TRIGGER_SHA="556c4deeeb3f659f8ad48a214da6c207de72a134"
EXPECTED_RECEIPTS_SHA256="3e1ba75095ebcd84847c663b87866e4535ba9efe9f9d9974ca65a75b7c8a8366"
EMPTY_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def api(url: str) -> bytes:
    token=os.environ.get("GITHUB_TOKEN","")
    req=urllib.request.Request(url,headers={
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        **({"Authorization":"Bearer "+token} if token else {})
    })
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def main() -> int:
    run=json.loads(api(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}"))
    assert run["status"]=="completed", run["status"]
    assert run["conclusion"]=="success", run["conclusion"]
    assert run["head_sha"]==TRIGGER_SHA, run["head_sha"]
    assert run["head_branch"]=="execute/livebench-replay72-v6-20261004-0918"

    jobs=json.loads(api(f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}/jobs?per_page=100"))
    job=[j for j in jobs["jobs"] if int(j["id"])==JOB_ID]
    assert len(job)==1
    assert job[0]["conclusion"]=="success"

    log=api(f"https://api.github.com/repos/{REPO}/actions/jobs/{JOB_ID}/logs").decode("utf-8","replace")
    pre=[]
    recs=[]
    terms=[]
    for line in log.splitlines():
        if "LIVEBENCH_V6_PRELAUNCH=" in line:
            pre.append(json.loads(line.split("LIVEBENCH_V6_PRELAUNCH=",1)[1]))
        if "LIVEBENCH_CASE_RECEIPT=" in line:
            recs.append(json.loads(line.split("LIVEBENCH_CASE_RECEIPT=",1)[1]))
        if "LIVEBENCH_TERMINAL_RESULT=" in line:
            terms.append(json.loads(line.split("LIVEBENCH_TERMINAL_RESULT=",1)[1]))

    assert len(pre)==1, len(pre)
    p=pre[0]
    assert p["status"]=="PASS__V6_POINT_OF_USE_PRELAUNCH"
    assert p["compatible"] is True
    assert p["new_case_exposure_authorized"] is False
    assert p["terminal_cases_consumed"]==0
    assert p["activation_git_blob_sha"]=="c449329ad9e6e9ac001c5a1cdb2f3fa187fa49b3"
    assert p["candidate_git_blob_sha"]=="07e857f0a7095838cecbc6a79961fe9580673ee4"
    assert p["executor_git_blob_sha"]=="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
    assert p["point_of_use_root_git_blob_sha"]=="822d7a0e64b2e919a873526d111e7202c40e1f5b"
    assert p["added_scheduler_overlays"]==["root2_decision_only_evaluation"]

    assert len(recs)==72, len(recs)
    assert len({r["question_id"] for r in recs})==72
    policy=[r for r in recs if r.get("inference_error")=="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION"]
    exits=[r for r in recs if str(r.get("inference_error") or "").startswith("INFERENCE_EXIT_1:")]
    valid=[r for r in recs if not r.get("inference_error")]
    other=[r for r in recs if r not in policy and r not in exits and r not in valid]
    assert len(policy)==43, len(policy)
    assert len(exits)==29, len(exits)
    assert len(valid)==0, len(valid)
    assert len(other)==0, len(other)
    assert len({r["inference_error"].split(":",1)[1] for r in exits})==29
    assert all(r["response_sha256"]==EMPTY_SHA for r in recs)
    assert sum(float(r["score"]) for r in recs)==0.0

    assert len(terms)==1, len(terms)
    t=terms[0]
    assert t["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_THRESHOLD_EXECUTION_RESULT_V2"
    assert t["status"]=="FAIL_FORCED"
    assert t["terminal_cases_consumed"]==72
    assert t["replay_prefix_limit"]==72
    assert t["replay_only_no_new_case_exposure"] is True
    assert t["predicate_fail_forced"] is True
    assert t["predicate_pass_forced"] is False
    assert float(t["observed_score_mass"])==0.0
    assert float(t["conservative_full_population_upper_percent"])==64.0
    assert t["receipts_sha256"]==EXPECTED_RECEIPTS_SHA256
    assert t["promotion_authority"] is False
    assert t["acceptance_credit_authority"] is False
    assert int(t["incremental_spend_usd"])==0

    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_REPLAY72_V6_PUBLIC_RESULT_VERIFICATION_20261004_V1",
      "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_PUBLIC_RUN_AND_LOG_RECOMPUTATION__43_POLICY_BLOCK__29_UNLOCALIZED_EXIT__ZERO_VALID_RESPONSES__ZERO_CREDIT",
      "run_id":RUN_ID,
      "job_id":JOB_ID,
      "trigger_sha":TRIGGER_SHA,
      "terminal_cases_replayed":72,
      "new_cases_exposed":0,
      "valid_candidate_responses":0,
      "policy_blocked_post_prompt_capability_acquisition":43,
      "inference_exit_1":29,
      "unique_exit_hashes":29,
      "score_mass":0.0,
      "raw_executor_fail_forced":True,
      "receipts_sha256":EXPECTED_RECEIPTS_SHA256,
      "capability_fail_adjudicated":False,
      "root1_reopen_adjudicated":False,
      "acceptance_credit_delta":0
    }
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
