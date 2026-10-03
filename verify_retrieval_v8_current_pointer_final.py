#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json"
A=R/"canonical/governance/GLOBAL_RETRIEVAL_V8_EMPIRICAL_EXTENSION_ACTIVATION_V1.json"
V=R/"canonical/verification/GLOBAL_RETRIEVAL_V8_EMPIRICAL_EXTENSION_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
def blob(p):
 x=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
assert blob(P)=="548f89195f26ccecdbe96cef8a02aa806fafd765",blob(P)
assert blob(A)=="5597833707ac5e2a28a2ba3ede9b83f5ce175ae5",blob(A)
assert blob(V)=="6a3f32cbd9c9054344776b59bc5405b50792a5cb",blob(V)
p=json.loads(P.read_text());a=json.loads(A.read_text());v=json.loads(V.read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8_ENTRYPOINT_V2_BOUND__ZERO_CREDIT"
assert v["independent_runner"]["conclusion"]=="success"
ext=p["v8_empirical_extension"]
assert ext["activation_git_blob_sha"]==blob(A)
assert ext["verification_git_blob_sha"]==blob(V)
assert ext["conclusion"]=="success"
reg=ext["real_hidden_witness_regression"]
assert reg["case_count"]==104
assert reg["monotonic_pooled_top5_recall"]==1.0
assert reg["monotonic_pooled_top5_misses"]==0
assert reg["open_world_recall_claim"] is False
live=ext["live_empirical_routing"]
assert live["controller_v2_git_blob_sha"]=="66edae1bfb12f2d46b7018736651b3dd27ed1c03"
assert live["entrypoint_v2_git_blob_sha"]=="b34bb56b49a71c136c5a72e97acf7aeac94a3b97"
assert live["event_ledger_git_blob_sha"]=="0a3f5a3dd06150e24511b8bfcd1998f908c65ff5"
assert live["live_event_state_git_blob_sha"]=="6637540ad0f9da41217fe2614773d78b563d2259"
assert live["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert live["fixed_correlation_multiplier_used"] is False
assert live["fixed_source_independence_multiplier_used"] is False
assert p["mechanical_entrypoint"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is False
assert p["mechanical_entrypoint"]["superseded_for_current_plan_compilation_by"]=="canonical/runtime/global_retrieval_entrypoint_v2.py"
rules=set(p["hard_rules"])
for rule in (
 "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V2",
 "FINITE_HIDDEN_WITNESS_ARENA_IS_REGRESSION_EVIDENCE_NOT_A_LIVE_PROVIDER_ORACLE",
 "LIVE_RETRIEVAL_EVENTS_ARE_APPEND_ONLY",
 "FIXED_SOURCE_CORRELATION_AND_INDEPENDENCE_MULTIPLIERS_ARE_FORBIDDEN_FOR_CURRENT_EMPIRICAL_ROUTING",
):
 assert rule in rules,rule
assert p["incremental_spend_usd"]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V8_CURRENT_POINTER_FINAL_VERIFIED")
