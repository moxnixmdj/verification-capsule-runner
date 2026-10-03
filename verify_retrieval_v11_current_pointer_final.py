#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/v11_current_pointer_final.json","c85a66713d662a29c6ddec491c2028d9a9be96fa"),
 "c":("subjects/v11_candidate_pointer_verification_final.json","ab21c189081c25cb178609aacab23632fc41d9f8"),
 "a":("subjects/v11_activation_verification_final.json","35d9efe922071196abece96bf4db39d26525c557")
}
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
p=load("p");c=load("c");a=load("a")
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8__STRESS_V9__DUAL_EMPIRICAL_V11_ENTRYPOINT_V3_BOUND__ZERO_CREDIT"
assert c["independent_runner"]["conclusion"]=="success"
assert a["independent_runner"]["conclusion"]=="success"
assert p["v11_current_pointer_candidate_verification"]["git_blob_sha"]==F["c"][1]
assert p["v11_current_pointer_candidate_verification"]["conclusion"]=="success"
x=p["v11_dual_empirical_extension"]
assert x["activation_verification_git_blob_sha"]==F["a"][1]
assert x["controller_v3_git_blob_sha"]=="51acba67af90306be25fcfb055292a4233f97316"
assert x["entrypoint_v3_git_blob_sha"]=="f913c25bef03a500c7c8a5d2b44a27c39b3ef34d"
assert x["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert p["v8_empirical_extension"]["real_hidden_witness_regression"]["monotonic_pooled_top5_recall"]==1
assert p["v9_generated_stress_extension"]["finite_hidden_witness_recall"]==1
rules=set(p["hard_rules"])
for rule in (
 "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V3",
 "OPEN_WORLD_NOVELTY_AND_LABELED_PROVIDER_QUERY_FAMILY_RECOVERY_MUST_BOTH_INFORM_CURRENT_ROUTING",
 "TRANSPORT_FAILURES_MUST_NOT_ENTER_LABELED_RECALL_DENOMINATORS",
 "MEASURED_POOR_PROVIDER_QUERY_FAMILIES_ARE_DEMOTED_NOT_DISABLED",
 "UNMEASURED_PROVIDER_QUERY_FAMILIES_RETAIN_EXPLICIT_JEFFREYS_COLD_START",
): assert rule in rules,rule
assert p["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):assert p[k]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V11_CURRENT_POINTER_FINAL_VERIFIED")
