#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/v9_stress_activation.json","aa13e5b42b71430e17402893c70cabced5dcfa76"),
 "v9r":("subjects/v9_stress_arena_receipt.json","9abc46d4e673e4b02789f9cbd39ea19125b575b4"),
 "p":("subjects/current_v8_pointer.json","548f89195f26ccecdbe96cef8a02aa806fafd765"),
 "v8a":("subjects/v8_empirical_activation.json","5597833707ac5e2a28a2ba3ede9b83f5ce175ae5"),
 "v8ar":("subjects/v8_empirical_activation_receipt.json","6a3f32cbd9c9054344776b59bc5405b50792a5cb"),
 "v8rw":("subjects/v8_real_hidden_witness_receipt.json","3d37f0cff61d5603bdec0358762e854be3adde3a"),
}
def blob(p):
 x=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k]; q=R/p; assert blob(q)==s,(k,blob(q),s); return json.loads(q.read_text())
a=load("a");v9r=load("v9r");p=load("p");v8a=load("v8a");v8ar=load("v8ar");v8rw=load("v8rw")
assert str(p["status"]).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8")
assert a["base_current_authority"]["git_blob_sha"]==F["p"][1]
assert a["base_v8_empirical_extension"]["activation_git_blob_sha"]==F["v8a"][1]
assert a["base_v8_empirical_extension"]["activation_verification_git_blob_sha"]==F["v8ar"][1]
assert a["base_v8_empirical_extension"]["real_hidden_witness_verification_git_blob_sha"]==F["v8rw"][1]
assert v8ar["independent_runner"]["conclusion"]=="success"
assert v8rw["independent_runner"]["conclusion"]=="success"
assert v8rw["measured"]["monotonic_pooled_top5_recall"]==1.0
assert v9r["independent_runner"]["conclusion"]=="success"
m=v9r["measured"]
assert m["generated_hidden_witness_case_count"]==768
assert m["finite_hidden_witness_recall"]==1.0
assert m["queryless_ablation_fails"] is True
assert m["multilingual_ablation_fails"] is True
assert m["revision_history_ablation_fails"] is True
ext=a["generated_stress_extension"]
assert ext["verification_git_blob_sha"]==F["v9r"][1]
assert ext["generated_case_count"]==768 and ext["finite_hidden_witness_recall"]==1.0
assert ext["open_world_recall_claim"] is False
pol=set(a["mandatory_policy"])
assert "GLOBAL_RETRIEVAL_V8_EMPIRICAL_ENTRYPOINT_V2_REMAINS_THE_ONLY_CURRENT_AUTHORIZED_PLAN_COMPILER" in pol
assert "V9_GENERATED_STRESS_ARENA_IS_MANDATORY_REGRESSION_EVIDENCE_BUT_MUST_NOT_CALIBRATE_LIVE_PROVIDER_ROUTING" in pol
assert "REAL_104_CASE_HIDDEN_WITNESS_REPLAY_REMAINS_MANDATORY_AND_SEPARATE" in pol
assert a["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert a[k]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V9_STRESS_ACTIVATION_VERIFIED")
