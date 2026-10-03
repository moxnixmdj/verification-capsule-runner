#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/v11_activation.json","08d6e44391f31d1acbc6ac85658e45edaa1fd838"),
 "p":("subjects/v11_base_pointer.json","cb58ff10b7c3ac99da8cbee7b8aa0b76006f8dfe"),
 "v":("subjects/v11_subject_receipt.json","91a57904c684f5445d00c8b4244714e95317949d"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
a=load("a");p=load("p");v=load("v")
assert v["independent_runner"]["conclusion"]=="success"
assert a["base_current_authority"]["git_blob_sha"]==F["p"][1]
b=a["v11_labeled_calibration"]
assert b["verification_git_blob_sha"]==F["v"][1]
assert b["events_git_blob_sha"]=="a5d73e154f865865f1f2186c16e36921e834357a"
assert b["calibration_git_blob_sha"]=="e023c17d46dc6841b6a5df5506f9c21533407d1c"
assert b["controller_v3_git_blob_sha"]=="51acba67af90306be25fcfb055292a4233f97316"
assert b["entrypoint_v3_git_blob_sha"]=="f913c25bef03a500c7c8a5d2b44a27c39b3ef34d"
assert b["conclusion"]=="success"
m=a["measured_epoch"]
assert m["github_code_behavioral_full"]["trials"]==26 and m["github_code_behavioral_full"]["hits_at_10"]==0
assert m["github_code_technical_anchor_compressed"]["trials"]==13 and m["github_code_technical_anchor_compressed"]["hits_at_10"]==0
assert m["web_search_github_domain_direct_q1"]["trials"]==13 and m["web_search_github_domain_direct_q1"]["hits_at_10"]==2
assert m["github_repository_search_via_fetch"]["recall_denominator"]==0
pol=set(a["mandatory_policy"])
for rule in (
 "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V3",
 "PROVIDER_AND_QUERY_FAMILY_MUST_BE_CALIBRATED_JOINTLY",
 "TRANSPORT_FAILURES_MUST_NOT_ENTER_RECALL_DENOMINATORS",
 "UNMEASURED_PROVIDER_QUERY_FAMILIES_KEEP_EXPLICIT_JEFFREYS_COLD_START_PRIOR",
 "MEASURED_POOR_PROVIDER_QUERY_FAMILIES_ARE_DEMOTED_NOT_DISABLED",
 "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
):
 assert rule in pol,rule
assert a["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert a[k]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V11_ACTIVATION_VERIFIED")
