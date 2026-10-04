#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
LOG=ROOT/"LIVEBENCH_REPLAY72_V6.log"
EXPECTED_LOG_BLOB="6c9c89cd2f7e977405017cb5ddfa8033126f4bf2"
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(LOG)==EXPECTED_LOG_BLOB,(blob(LOG),EXPECTED_LOG_BLOB)
receipts=[];pre=None;terminal=None
for line in LOG.read_text().splitlines():
 if line.startswith("LIVEBENCH_V6_PRELAUNCH="):pre=json.loads(line.split("=",1)[1])
 elif line.startswith("LIVEBENCH_CASE_RECEIPT="):receipts.append(json.loads(line.split("=",1)[1]))
 elif line.startswith("LIVEBENCH_TERMINAL_RESULT="):terminal=json.loads(line.split("=",1)[1])
assert pre and terminal and len(receipts)==72
assert pre["status"]=="PASS__V6_POINT_OF_USE_PRELAUNCH"
assert pre["activation_git_blob_sha"]=="c449329ad9e6e9ac001c5a1cdb2f3fa187fa49b3"
assert pre["candidate_git_blob_sha"]=="07e857f0a7095838cecbc6a79961fe9580673ee4"
assert pre["executor_git_blob_sha"]=="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
policy=sum(r.get("inference_error")=="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION" for r in receipts)
exit1=[r.get("inference_error") for r in receipts if isinstance(r.get("inference_error"),str) and r["inference_error"].startswith("INFERENCE_EXIT_1:")]
valid=sum(r.get("inference_error") is None for r in receipts)
other=72-policy-len(exit1)-valid
assert (policy,len(exit1),valid,other)==(43,29,0,0),(policy,len(exit1),valid,other)
assert len(set(exit1))==29
assert all(float(r.get("score",0))==0.0 for r in receipts)
assert all(r.get("scoring_error") is None for r in receipts)
assert terminal["status"]=="FAIL_FORCED"
assert terminal["terminal_cases_consumed"]==72
assert terminal["observed_score_mass"]==0.0
assert terminal["predicate_fail_forced"] is True
out={
 "schema":"PROJECT_BRAIN_LIVEBENCH_V6_REPLAY72_TRUTH_VERIFICATION_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__MIXED_POLICY_AND_RUNTIME_FAILURE__PREDICATE_FAILURE_NOT_ADMISSIBLE",
 "execution_evidence_commit":"59c9a029027b7c3eed4bb80f22933e7ddb2ddfb1",
 "execution_log_git_blob_sha":EXPECTED_LOG_BLOB,
 "terminal_cases_consumed":72,
 "policy_blocked_count":policy,
 "runtime_exit_count":len(exit1),
 "valid_candidate_response_count":valid,
 "distinct_runtime_exit_hash_count":len(set(exit1)),
 "recorded_score_mass":0.0,
 "arithmetic_fail_forced":True,
 "predicate_failure_admissible":False,
 "root1_reopen_authorized":False,
 "reason":"RUNTIME_EXIT_MASS_REMAINS_CAUSALLY_UNCLASSIFIED",
 "next_required_action":"SANITIZE_AND_CLASSIFY_RUNTIME_BLOCKERS_WITHOUT_PROMPT_OR_RESPONSE_CONTENT__REPLAY_ONLY_ALREADY_EXPOSED_PREFIX",
 "acceptance_credit_delta":0,
 "promotion_authority":False,
}
print(json.dumps(out,sort_keys=True))
