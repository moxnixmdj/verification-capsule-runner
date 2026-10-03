#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/v10_activation.json","dd5db2766eff2ef3f1ccc5113ed855643d7dbb9e"),
 "r":("subjects/v10_executor_receipt.json","2da80da3227c3379d462b15a2f14165542175daa"),
 "p":("subjects/current_v9_pointer_for_v10.json","cb58ff10b7c3ac99da8cbee7b8aa0b76006f8dfe"),
 "v9":("subjects/v9_pointer_receipt_for_v10.json","e190ead3ad5994fe76be407aafd93d186c1a96e6"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
a=load("a");r=load("r");p=load("p");v9=load("v9")
assert p["status"].endswith("GENERATED_STRESS_V9_BOUND__ZERO_CREDIT")
assert v9["independent_runner"]["conclusion"]=="success"
assert r["independent_runner"]["conclusion"]=="success"
assert a["base_current_authority"]["git_blob_sha"]==F["p"][1]
li=a["live_instrumentation"]
assert li["executor_git_blob_sha"]=="a63a4991daa3dca147f373b7890151f07afd3f4e"
assert li["test_git_blob_sha"]=="6f28c317ec231f1e912e4ad74f5326b9a39b9c0e"
assert li["verification_git_blob_sha"]==F["r"][1]
pol=set(a["mandatory_policy"])
for rule in (
 "ALL_CURRENT_LIVE_PROVIDER_EXECUTION_USED_FOR_EMPIRICAL_ROUTING_MUST_EMIT_ONE_APPEND_ONLY_MEASURED_EVENT_PER_EXECUTED_ACTION",
 "DUPLICATE_EPISODE_ACTION_EXECUTION_MUST_FAIL_BEFORE_PROVIDER_CALL",
 "LIVE_LATENCY_MUST_BE_MEASURED_WITH_PERF_COUNTER_OR_STRONGER_MONOTONIC_CLOCK__NEVER_INVENTED",
 "PROVIDER_OR_CANDIDATE_SELF_CERTIFICATION_OF_SUFFICIENCY_IS_FORBIDDEN",
 "FAILED_RETRYABLE_PROVIDER_CALLS_MUST_BE_RECORDED_AS_FAILURE_EVIDENCE_AND_MUST_NOT_BECOME_NEGATIVE_EXISTENCE_PROOF",
):
 assert rule in pol,rule
assert "NO_CLAIM_EXISTING_HISTORICAL_ZERO_LATENCY_EVENT_IS_RETROACTIVELY_REMEASURED" in a["hard_nonclaims"]
assert "NO_CLAIM_LIVE_CALIBRATION_IS_MATURE_BEFORE_ENOUGH_NEW_MEASURED_EVENTS_ACCUMULATE" in a["hard_nonclaims"]
assert a["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert a[k]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V10_LIVE_INSTRUMENTATION_ACTIVATION_VERIFIED")
