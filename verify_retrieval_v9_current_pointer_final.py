#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/current_v9_pointer.json","cb58ff10b7c3ac99da8cbee7b8aa0b76006f8dfe"),
 "a":("subjects/v9_activation.json","aa13e5b42b71430e17402893c70cabced5dcfa76"),
 "ar":("subjects/v9_activation_receipt.json","2ba0906603e02b9bba6fdfa2575bcd853e4d3534"),
 "v8":("subjects/v8_pointer_final_receipt.json","2f1a2824146355d92cd1dffe62a0af30243ff935"),
}
def blob(p):
 x=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
p=load("p");a=load("a");ar=load("ar");v8=load("v8")
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8_ENTRYPOINT_V2_BOUND__GENERATED_STRESS_V9_BOUND__ZERO_CREDIT"
assert v8["independent_runner"]["conclusion"]=="success"
assert ar["independent_runner"]["conclusion"]=="success"
ext=p["v9_generated_stress_extension"]
assert ext["activation_git_blob_sha"]==F["a"][1]
assert ext["activation_verification_git_blob_sha"]==F["ar"][1]
assert ext["generated_hidden_witness_arena_git_blob_sha"]=="7cf00ad65bc160f4b3d1e7d90233c52f496a1bd1"
assert ext["generated_hidden_witness_verification_git_blob_sha"]=="9abc46d4e673e4b02789f9cbd39ea19125b575b4"
assert ext["generated_case_count"]==768
assert ext["finite_hidden_witness_recall"]==1
assert ext["mandatory_regression_only"] is True
assert ext["permitted_to_calibrate_live_provider_routing"] is False
assert ext["open_world_recall_claim"] is False
v8ext=p["v8_empirical_extension"]
assert v8ext["real_hidden_witness_regression"]["case_count"]==104
assert v8ext["real_hidden_witness_regression"]["monotonic_pooled_top5_recall"]==1
assert v8ext["live_empirical_routing"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert v8ext["live_empirical_routing"]["fixed_correlation_multiplier_used"] is False
assert v8ext["live_empirical_routing"]["fixed_source_independence_multiplier_used"] is False
rules=set(p["hard_rules"])
assert "FROZEN_768_CASE_GENERATED_HIDDEN_WITNESS_RECALL_MUST_NOT_REGRESS_BELOW_1_0_WITHOUT_EXPLICIT_FAIL_CLOSED_SUPERSESSION" in rules
assert "GENERATED_STRESS_ARENA_MUST_NOT_CALIBRATE_LIVE_PROVIDER_ROUTING" in rules
assert "QUERYLESS_MULTILINGUAL_AND_REVISION_HISTORY_ABLATIONS_MUST_CONTINUE_TO_FAIL" in rules
assert p["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert p[k]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V9_CURRENT_POINTER_FINAL_VERIFIED")
