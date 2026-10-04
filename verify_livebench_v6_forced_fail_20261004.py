#!/usr/bin/env python3
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_v6_forced_fail_20261004"
REC=SUB/"reconciliation.json"
LOG=SUB/"execution.log"
EXIT=SUB/"exit_code.txt"
EXPECTED={
 REC:"b1e14f11d97673a499f2d9a5e2c708d9aba969fb",
 LOG:"6c9c89cd2f7e977405017cb5ddfa8033126f4bf2",
 EXIT:"573541ac9702dd3969c9bc859d2b91ec1f7e6e56",
}
def blob(p):
 d=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
for p,h in EXPECTED.items():
 assert blob(p)==h,(p,blob(p),h)

rec=json.loads(REC.read_text())
assert EXIT.read_text().strip()=="0"
cases=[]
terminal=None
prelaunch=None
for line in LOG.read_text().splitlines():
 if line.startswith("LIVEBENCH_CASE_RECEIPT="):
  cases.append(json.loads(line.split("=",1)[1]))
 elif line.startswith("LIVEBENCH_TERMINAL_RESULT="):
  terminal=json.loads(line.split("=",1)[1])
 elif line.startswith("LIVEBENCH_V6_PRELAUNCH="):
  prelaunch=json.loads(line.split("=",1)[1])

assert prelaunch and prelaunch["status"]=="PASS__V6_POINT_OF_USE_PRELAUNCH"
assert prelaunch["compatible"] is True
assert prelaunch["new_case_exposure_authorized"] is False
assert len(cases)==72
ids=[x["question_id"] for x in cases]
assert len(set(ids))==72
assert all(float(x["score"])==0.0 for x in cases)
assert all(x.get("scoring_error") is None for x in cases)
assert all(x.get("response_sha256")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" for x in cases)
policy=sum(str(x.get("inference_error") or "").startswith("POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION") for x in cases)
exit1=sum(str(x.get("inference_error") or "").startswith("INFERENCE_EXIT_1:") for x in cases)
assert policy==43
assert exit1==29
assert policy+exit1==72

population=200
threshold=65.7
observed_mass=sum(float(x["score"]) for x in cases)
remaining=population-len(cases)
upper=100.0*(observed_mass+remaining)/population
assert observed_mass==0.0
assert remaining==128
assert upper==64.0
assert upper < threshold
assert terminal is not None
assert terminal["status"]=="FAIL_FORCED"
assert terminal["predicate_fail_forced"] is True
assert terminal["predicate_pass_forced"] is False
assert float(terminal["conservative_full_population_upper_percent"])==upper
assert int(terminal["terminal_cases_consumed"])==72
assert terminal["replay_only_no_new_case_exposure"] is True
assert float(terminal["incremental_spend_usd"])==0.0

tp=rec["threshold_proof"]
assert tp["predicate_pass_mathematically_possible_for_frozen_candidate"] is False
assert tp["further_case_exposure_required_to_decide_predicate_for_frozen_candidate"] is False
assert float(tp["conservative_full_population_upper_percent"])==64.0
assert rec["accounting"]["acceptance_credit_delta"]==0
assert rec["execution_authority"] is False
assert rec["promotion_authority"] is False

print(json.dumps({
 "status":"PASS__LIVEBENCH_V6_FORCED_FAIL_INDEPENDENTLY_VERIFIED",
 "case_count":72,
 "unique_question_ids":72,
 "observed_score_mass":observed_mass,
 "remaining_unseen":remaining,
 "best_case_full_population_upper_percent":upper,
 "threshold_percent":threshold,
 "predicate_false_for_frozen_candidate":True,
 "additional_case_exposure_needed":False,
 "policy_blocked_count":policy,
 "inference_exit_count":exit1,
 "acceptance_credit_delta":0
},sort_keys=True))
