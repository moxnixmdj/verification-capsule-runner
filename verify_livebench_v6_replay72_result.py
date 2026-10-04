#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
RUN_ID=37191913947
JOB_ID=111405727774
HEAD_SHA="c3c14e3143aa6f0b87cd57cbd398c49059f64b0a"
ACTIVATION_SHA="c449329ad9e6e9ac001c5a1cdb2f3fa187fa49b3"
EMPTY_SHA256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

run=json.loads((ROOT/"livebench_v6_run.json").read_text())
jobs=json.loads((ROOT/"livebench_v6_jobs.json").read_text())
log=(ROOT/"livebench_v6_job.log").read_text(errors="replace")

assert run["id"]==RUN_ID
assert run["name"]=="Execute authorized LiveBench V6 replay72"
assert run["event"]=="push"
assert run["head_sha"]==HEAD_SHA
assert run["status"]=="completed"
assert run["conclusion"]=="success"
job=next(j for j in jobs["jobs"] if j["id"]==JOB_ID)
assert job["name"]=="replay72"
assert job["status"]=="completed"
assert job["conclusion"]=="success"

receipts=[]
summary=None
prelaunch=None
for line in log.splitlines():
    if "LIVEBENCH_V6_PRELAUNCH=" in line:
        prelaunch=json.loads(line.split("LIVEBENCH_V6_PRELAUNCH=",1)[1])
    if "LIVEBENCH_CASE_RECEIPT=" in line:
        receipts.append(json.loads(line.split("LIVEBENCH_CASE_RECEIPT=",1)[1]))
    if "LIVEBENCH_TERMINAL_RESULT=" in line:
        summary=json.loads(line.split("LIVEBENCH_TERMINAL_RESULT=",1)[1])

assert prelaunch is not None
assert prelaunch["status"]=="PASS__V6_POINT_OF_USE_PRELAUNCH"
assert prelaunch["compatible"] is True
assert prelaunch["activation_git_blob_sha"]==ACTIVATION_SHA
assert prelaunch["new_case_exposure_authorized"] is False
assert prelaunch["terminal_cases_consumed"]==0

assert len(receipts)==72
policy=sum(r["inference_error"]=="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION" for r in receipts)
exits=sum(isinstance(r["inference_error"],str) and r["inference_error"].startswith("INFERENCE_EXIT_1:") for r in receipts)
valid=sum(r["inference_error"] is None for r in receipts)
nonzero=sum(float(r["score"])>0 for r in receipts)
assert policy==43, policy
assert exits==29, exits
assert valid==0, valid
assert nonzero==0, nonzero
assert all(r["response_sha256"]==EMPTY_SHA256 for r in receipts)
assert all(float(r["score"])==0.0 for r in receipts)

assert summary is not None
assert summary["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_THRESHOLD_EXECUTION_RESULT_V2"
assert summary["status"]=="FAIL_FORCED"
assert summary["benchmark_id"]=="LIVEBENCH_IF_2026_06_25"
assert summary["population_count"]==200
assert summary["replay_prefix_limit"]==72
assert summary["replay_only_no_new_case_exposure"] is True
assert summary["terminal_cases_consumed"]==72
assert float(summary["observed_score_mass"])==0.0
assert float(summary["observed_mean_percent"])==0.0
assert float(summary["conservative_full_population_lower_percent"])==0.0
assert float(summary["conservative_full_population_upper_percent"])==64.0
assert summary["predicate_fail_forced"] is True
assert summary["predicate_pass_forced"] is False
assert float(summary["threshold_percent"])==65.7
assert float(summary["threshold_mass"])==131.4
assert summary["activation_blob_sha"]==ACTIVATION_SHA
assert summary["incremental_spend_usd"]==0
assert summary["paid_external_model_or_api_used"] is False
assert summary["promotion_authority"] is False
assert summary["acceptance_credit_authority"] is False

receipt={
  "schema":"PROJECT_BRAIN_LIVEBENCH_V6_REPLAY72_RESULT_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
  "status":"INDEPENDENT_PUBLIC_LOG_REDUCTION_PASS__EXACT_REPLAY72__FAIL_FORCED_FOR_FROZEN_CANDIDATE__ZERO_VALID_RESPONSES__ZERO_CREDIT",
  "execution":{
    "repository":"moxnixmdj/verification-capsule-runner",
    "workflow_run_id":RUN_ID,
    "workflow_job_id":JOB_ID,
    "head_sha":HEAD_SHA,
    "conclusion":"success"
  },
  "prelaunch":{
    "compatible":True,
    "activation_git_blob_sha":ACTIVATION_SHA,
    "point_of_use_root_git_blob_sha":prelaunch["point_of_use_root_git_blob_sha"],
    "added_scheduler_overlays":prelaunch["added_scheduler_overlays"]
  },
  "observed":{
    "case_receipts":72,
    "valid_candidate_responses":0,
    "policy_blocked_post_prompt_acquisition":43,
    "inference_exit_1":29,
    "nonzero_score_cases":0,
    "observed_score_mass":0,
    "conservative_full_population_upper_percent":64.0,
    "threshold_percent":65.7,
    "predicate_fail_forced_by_recorded_scores":True,
    "receipts_sha256":summary["receipts_sha256"]
  },
  "causal_interpretation":{
    "all_72_empty_due_to_inference_or_policy_failure":True,
    "semantic_task_failure_demonstrated":False,
    "capability_gap_proved":False,
    "root1_reopen_authorized":False,
    "candidate_threshold_failure_recorded":True
  },
  "authority":{
    "acceptance_reduction":False,
    "promotion":False,
    "new_case_exposure":False,
    "additional_replay_epoch":False
  },
  "accounting":{
    "incremental_spend_usd":0,
    "new_case_exposure_count":0,
    "replayed_existing_case_count":72,
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0
  }
}
print(json.dumps(receipt,sort_keys=True))
