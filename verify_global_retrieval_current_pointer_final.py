#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/global_retrieval_current_pointer_final.json","347480f0cdef4195c7f5c7e8efec5a6192f08194"),
 "v":("subjects/global_retrieval_pointer_candidate_verification_final.json","094f31c1c22e12961d86dc93fca06a695f6bb33a"),
}
def blob(q):
 x=q.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
p=load("p");v=load("v")
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__ZERO_CREDIT"
assert p["current_global_retrieval_authority"]["git_blob_sha"]=="335b285d27faa16913c9ec661cdf0b6a25057726"
assert p["final_pointer_candidate_verification"]["git_blob_sha"]==F["v"][1]
assert p["final_pointer_candidate_verification"]["conclusion"]=="success"
assert v["independent_runner"]["conclusion"]=="success"
assert p["finite_adversarial_coverage"]["case_count"]==4096
assert p["finite_adversarial_coverage"]["architectural_failure_class_mechanism_coverage"]==1.0
assert p["finite_adversarial_coverage"]["open_world_recall_claim"] is False
pol=p["policy"]
assert pol["candidate_memory"].startswith("MONOTONIC")
assert pol["zero_lexical_bridge"].startswith("QUERYLESS_BOUNDED_ENUMERATION_REQUIRED")
assert pol["correlated_sources"].startswith("DISCOUNT")
assert pol["open_world_miss"].startswith("UNKNOWN")
assert p["search_engine_architecture"]["selected"].startswith("HYBRID__BRAIN_CONTROLLER")
assert p["incremental_spend_usd"]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_CURRENT_POINTER_FINAL_VERIFIED")
