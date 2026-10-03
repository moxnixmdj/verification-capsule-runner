#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/current_v10_pointer.json","b69d3ca8169a7cc1b612d4b8976872b794e93517"),
 "a":("subjects/v10_activation_final.json","dd5db2766eff2ef3f1ccc5113ed855643d7dbb9e"),
 "ar":("subjects/v10_activation_receipt_final.json","d49765d721efc179e2a4b1f765701f8338e2d430"),
 "er":("subjects/v10_executor_receipt_final.json","2da80da3227c3379d462b15a2f14165542175daa"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
p=load("p");a=load("a");ar=load("ar");er=load("er")
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8_ENTRYPOINT_V2_BOUND__GENERATED_STRESS_V9_BOUND__LIVE_INSTRUMENTATION_V10_BOUND__ZERO_CREDIT"
assert ar["independent_runner"]["conclusion"]=="success"
assert er["independent_runner"]["conclusion"]=="success"
ext=p["v10_live_instrumentation_extension"]
assert ext["activation_git_blob_sha"]==F["a"][1]
assert ext["activation_verification_git_blob_sha"]==F["ar"][1]
assert ext["executor_verification_git_blob_sha"]==F["er"][1]
assert ext["executor_git_blob_sha"]=="a63a4991daa3dca147f373b7890151f07afd3f4e"
assert ext["mandatory_for_live_provider_execution_used_for_empirical_routing"] is True
assert ext["duplicate_episode_action_execution_forbidden"] is True
assert ext["measured_latency_required"] is True
assert ext["historical_zero_latency_event_not_retroactively_remeasured"] is True
assert p["v9_generated_stress_extension"]["finite_hidden_witness_recall"]==1
assert p["v8_empirical_extension"]["real_hidden_witness_regression"]["monotonic_pooled_top5_recall"]==1
rules=set(p["hard_rules"])
for rule in (
 "ALL_CURRENT_LIVE_PROVIDER_EXECUTION_USED_FOR_EMPIRICAL_ROUTING_MUST_USE_RETRIEVAL_LIVE_INSTRUMENTED_EXECUTOR_V1_OR_A_FAIL_CLOSED_VERIFIED_SUPERSESSION",
 "EVERY_CURRENT_LIVE_PROVIDER_ACTION_USED_FOR_EMPIRICAL_ROUTING_MUST_APPEND_EXACTLY_ONE_MEASURED_EVENT",
 "DUPLICATE_EPISODE_ACTION_EXECUTION_MUST_FAIL_BEFORE_PROVIDER_CALL",
 "HISTORICAL_ZERO_LATENCY_EVENTS_MUST_NOT_BE_RETROACTIVELY_ASSIGNED_INVENTED_TIMING",
):
 assert rule in rules,rule
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V10_CURRENT_POINTER_FINAL_VERIFIED")
