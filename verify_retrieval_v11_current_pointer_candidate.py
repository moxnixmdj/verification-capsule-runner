#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"subjects/v11_current_pointer_candidate.json"
V=R/"subjects/v11_activation_verification.json"
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(P)=="3f2320220ebb218f16b95c18e3b38dee26d1b533",blob(P)
assert blob(V)=="35d9efe922071196abece96bf4db39d26525c557",blob(V)
p=json.loads(P.read_text());v=json.loads(V.read_text())
assert p["status"]=="ACTIVE_CANDIDATE__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V8__STRESS_V9__DUAL_EMPIRICAL_V11_ENTRYPOINT_V3_BOUND__FINAL_POINTER_VERIFICATION_REQUIRED__ZERO_CREDIT"
assert v["independent_runner"]["conclusion"]=="success"
x=p["v11_dual_empirical_extension"]
assert x["activation_git_blob_sha"]=="08d6e44391f31d1acbc6ac85658e45edaa1fd838"
assert x["activation_verification_git_blob_sha"]==blob(V)
assert x["subject_verification_git_blob_sha"]=="91a57904c684f5445d00c8b4244714e95317949d"
assert x["controller_v3_git_blob_sha"]=="51acba67af90306be25fcfb055292a4233f97316"
assert x["entrypoint_v3_git_blob_sha"]=="f913c25bef03a500c7c8a5d2b44a27c39b3ef34d"
assert x["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert p["v8_empirical_extension"]["live_empirical_routing"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert p["v9_generated_stress_extension"]["mandatory_regression_only"] is True
rules=set(p["hard_rules"])
assert "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V3" in rules
assert "MEASURED_POOR_PROVIDER_QUERY_FAMILIES_ARE_DEMOTED_NOT_DISABLED" in rules
assert "TRANSPORT_FAILURES_MUST_NOT_ENTER_LABELED_RECALL_DENOMINATORS" in rules
assert p["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):assert p[k]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V11_CURRENT_POINTER_CANDIDATE_VERIFIED")
