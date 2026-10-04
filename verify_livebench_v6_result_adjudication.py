#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request

BASE="https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner"
API="https://api.github.com/repos/moxnixmdj/verification-capsule-runner"

def get(url: str) -> bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-livebench-v6-adjudicator"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def raw(commit,path):
    return get(f"{BASE}/{commit}/{path}")

# Immutable public evidence and control-plane bytes.
log_b=raw("59c9a029027b7c3eed4bb80f22933e7ddb2ddfb1","LIVEBENCH_REPLAY72_V6.log")
exit_b=raw("59c9a029027b7c3eed4bb80f22933e7ddb2ddfb1","LIVEBENCH_REPLAY72_V6_EXIT_CODE")
executor_b=raw("7db0fdf369b7b9dbd4f803897f2c39fe578f5400","execute_livebench_if_replay72_v4_candidate.py")
launcher_b=raw("b1e82a458a20fa50c8c9defb55e5100b14eb279d","launch_livebench_replay72_v6.py")
activation_b=raw("b1e82a458a20fa50c8c9defb55e5100b14eb279d","subject/livebench_retry_v6_20261004/activation.json")
candidate_b=raw("b1e82a458a20fa50c8c9defb55e5100b14eb279d","subject/livebench_retry_v6_20261004/candidate.json")
workflow_b=raw("de7ef63fffccbe98fe2cc55e0121139eb525e34d",".github/workflows/execute-livebench-replay72-v6.yml")

expected={
 "log":"6c9c89cd2f7e977405017cb5ddfa8033126f4bf2",
 "exit":"573541ac9702dd3969c9bc859d2b91ec1f7e6e56",
 "executor":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
 "launcher":"e0e2c3581b389efd1c5cab4b4eff78762d1ec61b",
 "activation":"c449329ad9e6e9ac001c5a1cdb2f3fa187fa49b3",
 "candidate":"07e857f0a7095838cecbc6a79961fe9580673ee4",
 "workflow":"2165618f4910265914d0d8bfc6c719c29ae56e43",
}
actual={
 "log":git_blob(log_b),"exit":git_blob(exit_b),"executor":git_blob(executor_b),
 "launcher":git_blob(launcher_b),"activation":git_blob(activation_b),
 "candidate":git_blob(candidate_b),"workflow":git_blob(workflow_b),
}
assert actual==expected,(actual,expected)
assert exit_b.decode().strip()=="0"

# Bind to the actual successful GitHub Actions execution.
run=json.loads(get(API+"/actions/runs/37191763314").decode())
assert run["name"]=="Execute LiveBench replay72 V6"
assert run["head_sha"]=="de7ef63fffccbe98fe2cc55e0121139eb525e34d"
assert run["head_branch"]=="execute/livebench-replay72-v6-20261004"
assert run["event"]=="push" and run["status"]=="completed" and run["conclusion"]=="success"
jobs=json.loads(get(API+"/actions/runs/37191763314/jobs?per_page=100").decode())["jobs"]
assert len(jobs)==1
job=jobs[0]
assert job["name"]=="execute" and job["conclusion"]=="success"
steps={x["name"]:x["conclusion"] for x in job["steps"]}
for k in (
 "Verify exact launcher and executor bytes",
 "Execute exact verified replay72 epoch",
 "Persist immutable replay evidence",
 "Run actions/upload-artifact@v4",
):
    assert steps.get(k)=="success",(k,steps.get(k))
arts=json.loads(get(API+"/actions/runs/37191763314/artifacts?per_page=100").decode())["artifacts"]
art=[a for a in arts if a["name"]=="livebench-replay72-v6-evidence"]
assert len(art)==1
assert art[0]["digest"]=="sha256:ac396bd9e65e1b1dd5a7d51bf1df8a586cb075db88ad6ca2e2751adb126aa82c"
assert art[0]["expired"] is False

activation=json.loads(activation_b)
candidate=json.loads(candidate_b)
assert activation["authority"]["execution"] is True
assert activation["authority"]["replay_existing_prefix"] is True
assert activation["authority"]["new_case_exposure"] is False
assert activation["authority"]["global_fresh_reality"] is False
assert activation["authority"]["promotion"] is False
assert activation["authority"]["acceptance_credit"] is False
assert activation["exact_binding"]["replay_case_count"]==72
assert activation["exact_binding"]["population_count"]==200
assert float(activation["exact_binding"]["threshold_percent"])==65.7
assert "NO_CASE_73_OR_LATER" in activation["hard_rules"]
assert "NO_CANDIDATE_BYTE_MUTATION" in activation["hard_rules"]
assert "NO_POST_PROMPT_CAPABILITY_ACQUISITION" in activation["hard_rules"]

# The V6 candidate required the replay to classify each attempted case.
assert candidate["retry_scope"]["first_required_replay"]=="EXACT_ALREADY_ATTEMPTED_72_CASE_PREFIX_ONLY"
assert candidate["retry_scope"]["new_case_exposure_before_replay_validation"] is False
assert candidate["retry_scope"]["replay_result_must_distinguish_valid_candidate_response_from_policy_blocked_or_runtime_error"] is True
assert candidate["executor_verification"]["executor_git_blob_sha"]==expected["executor"]
assert candidate["executor_verification"]["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS"
assert candidate["executor_verification"]["post_prompt_acquisition_loader_denied"] is True

# Verify the precommitted executor's negative-outcome scoring rule, not merely its final printout.
executor=executor_b.decode()
required_executor_fragments=[
 'if inf_err:',
 'score,allok,n,followed,score_err=0.0,False,len(q.get("instruction_id_list") or []),0,None',
 'upper=cumulative+remaining',
 'if upper < THRESHOLD_MASS:',
 'verdict="FAIL_FORCED"',
 '"predicate_fail_forced":cumulative+(POPULATION-consumed) < THRESHOLD_MASS',
]
for frag in required_executor_fragments:
    assert frag in executor,frag

# Parse immutable execution evidence.
receipts=[]
prelaunch=None
final=None
for line in log_b.decode().splitlines():
    if line.startswith("LIVEBENCH_V6_PRELAUNCH="):
        prelaunch=json.loads(line.split("=",1)[1])
    elif line.startswith("LIVEBENCH_CASE_RECEIPT="):
        receipts.append(json.loads(line.split("=",1)[1]))
    elif line.startswith("LIVEBENCH_TERMINAL_RESULT="):
        final=json.loads(line.split("=",1)[1])

assert prelaunch is not None and final is not None
assert prelaunch["status"]=="PASS__V6_POINT_OF_USE_PRELAUNCH"
assert prelaunch["compatible"] is True
assert prelaunch["new_case_exposure_authorized"] is False
assert prelaunch["activation_git_blob_sha"]==expected["activation"]
assert prelaunch["candidate_git_blob_sha"]==expected["candidate"]
assert prelaunch["executor_git_blob_sha"]==expected["executor"]

assert len(receipts)==72
assert len({r["question_id"] for r in receipts})==72
assert all(r["score"]==0.0 for r in receipts)
assert all(r["response_sha256"]=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" for r in receipts)
assert all(r["scoring_error"] is None for r in receipts)
policy=sum(1 for r in receipts if str(r["inference_error"]).startswith("POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION"))
runtime=sum(1 for r in receipts if str(r["inference_error"]).startswith("INFERENCE_EXIT_1:"))
other=len(receipts)-policy-runtime
assert policy==43 and runtime==29 and other==0

# Recompute the content-addressed receipt root exactly as the executor did.
raw=json.dumps(receipts,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
receipts_sha=hashlib.sha256(raw).hexdigest()
assert receipts_sha=="cdfa9b888ddff1970864af7057c305c0fca80327882252c3dc9d6da8336fb715"
assert final["receipts_sha256"]==receipts_sha
assert final["terminal_cases_consumed"]==72
assert final["observed_score_mass"]==0.0
assert final["status"]=="FAIL_FORCED"
assert final["predicate_fail_forced"] is True
assert final["predicate_pass_forced"] is False

# Independent threshold arithmetic.
population=200
threshold_percent=65.7
threshold_mass=population*threshold_percent/100.0
observed_mass=sum(float(r["score"]) for r in receipts)
remaining=population-len(receipts)
upper_mass=observed_mass+remaining
upper_percent=100.0*upper_mass/population
assert threshold_mass==131.4
assert remaining==128
assert upper_mass==128.0
assert upper_percent==64.0
assert upper_mass < threshold_mass
assert float(final["conservative_full_population_upper_percent"])==64.0

# Legacy inner summary root/frontier fields are transport metadata from the preverified executor.
# V6 authority deliberately moves point-of-use root admissibility to the outer launcher.
assert final["bound_root_blob_sha"]=="601e82d00104b4ed36ee5968ad966a0c02e627c1"
assert prelaunch["point_of_use_root_git_blob_sha"]=="822d7a0e64b2e919a873526d111e7202c40e1f5b"
assert activation["root_binding"]["mode"]=="BASE_ROOT_PLUS_POINT_OF_USE_SCHEDULER_ONLY_COMPATIBILITY"
assert activation["launch_contract"]["launcher_must_verify_point_of_use_root_compatibility"] is True

out={
 "schema":"PROJECT_BRAIN_LIVEBENCH_V6_RESULT_ADJUDICATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
 "status":"PASS__EXECUTION_INTEGRITY_AND_FROZEN_EXECUTOR_THRESHOLD_FAIL_FORCED__NEGATIVE_ACCEPTANCE_EVIDENCE_ELIGIBLE",
 "workflow_run_id":37191763314,
 "workflow_job_id":job["id"],
 "artifact_id":art[0]["id"],
 "artifact_digest":art[0]["digest"],
 "evidence_commit":"59c9a029027b7c3eed4bb80f22933e7ddb2ddfb1",
 "log_git_blob_sha":expected["log"],
 "activation_git_blob_sha":expected["activation"],
 "candidate_git_blob_sha":expected["candidate"],
 "executor_git_blob_sha":expected["executor"],
 "launcher_git_blob_sha":expected["launcher"],
 "terminal_cases_consumed":72,
 "policy_blocked_cases":43,
 "inference_exit_cases":29,
 "valid_nonempty_responses":0,
 "observed_score_mass":0.0,
 "remaining_case_count":128,
 "maximum_possible_full_population_score_mass":128.0,
 "maximum_possible_full_population_percent":64.0,
 "threshold_percent":65.7,
 "threshold_mass":131.4,
 "predicate_fail_forced_under_frozen_executor_semantics":True,
 "negative_acceptance_evidence_eligible":True,
 "root1_reclassification_authorized_by_this_verifier":False,
 "acceptance_promotion_authorized":False,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "new_case_exposure":0,
 "hard_nonclaims":[
   "NO_AUTOMATIC_CANONICAL_ROOT1_MUTATION",
   "NO_ACCEPTANCE_PROMOTION",
   "NO_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
   "NO_CASE_73_OR_LATER_EXPOSED",
   "NO_CLAIM_THAT_EVERY_INFERENCE_EXIT_HAS_THE_SAME_INTERNAL_CAUSE"
 ]
}
print(json.dumps(out,sort_keys=True))
