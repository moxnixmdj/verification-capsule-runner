#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/global_retrieval_current_pointer.json","dd85a98714e6bade6a4b03e2a8d45f795ba21500"),
 "a":("subjects/global_retrieval_v6_activation_for_pointer.json","335b285d27faa16913c9ec661cdf0b6a25057726"),
 "v":("subjects/global_retrieval_v6_activation_receipt_for_pointer.json","9d0e031501a68f3a009b371cf9bde4d86fe34656"),
}
def blob(q):
 x=q.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k]; q=R/p; assert blob(q)==s,(k,blob(q),s); return json.loads(q.read_text())
p=load("p"); a=load("a"); v=load("v")
assert v["independent_runner"]["conclusion"]=="success"
assert p["current_global_retrieval_authority"]["git_blob_sha"]==F["a"][1]
assert p["independent_activation_verification"]["git_blob_sha"]==F["v"][1]
assert p["independent_activation_verification"]["conclusion"]=="success"
assert p["finite_adversarial_coverage"]["case_count"]==4096
assert p["finite_adversarial_coverage"]["architectural_failure_class_mechanism_coverage"]==1.0
assert p["finite_adversarial_coverage"]["open_world_recall_claim"] is False
pol=p["policy"]
assert pol["external_search_engines"].startswith("CANDIDATE_GENERATORS_ONLY")
assert pol["bounded_authoritative_enumeration"]=="PREFERRED_WHEN_AVAILABLE"
assert pol["zero_lexical_bridge"].startswith("QUERYLESS_BOUNDED_ENUMERATION_REQUIRED")
assert pol["candidate_memory"].startswith("MONOTONIC")
assert pol["correlated_sources"].startswith("DISCOUNT")
assert pol["open_world_miss"].startswith("UNKNOWN")
assert pol["real_false_negative"].startswith("COMPILE_TO_PERMANENT")
assert p["search_engine_architecture"]["selected"].startswith("HYBRID__BRAIN_CONTROLLER")
assert p["incremental_spend_usd"]==0
assert p["acceptance_credit_delta"]==0 and p["family_credit_delta"]==0 and p["capability_credit_delta"]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_CURRENT_POINTER_CANDIDATE_VERIFIED")
