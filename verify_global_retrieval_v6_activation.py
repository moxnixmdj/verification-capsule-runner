#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/global_retrieval_v6_activation.json","335b285d27faa16913c9ec661cdf0b6a25057726"),
 "c":("subjects/global_retrieval_v6_core_receipt.json","47b43d15919172b1752e8658bff3194c4491a132"),
 "v5":("subjects/retrieval_v5_activation.json","8b8b80d43972bb7113b193baaf21dbda292d595e"),
 "v5r":("subjects/retrieval_v5_activation_receipt.json","acd898bdea67ef0337e33b4335426fbe0dd7320d")
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
a=load("a");c=load("c");v5=load("v5");v5r=load("v5r")
assert c["independent_runner"]["conclusion"]=="success"
assert c["verified"]["finite_torture_case_count"]==4096
assert c["verified"]["finite_architectural_failure_class_coverage"]==1.0
assert v5r["independent_runner"]["conclusion"]=="success"
assert a["verified_v5_substrate"]["v5_activation"]["git_blob_sha"]==F["v5"][1]
assert a["verified_v5_substrate"]["v5_activation_verification"]["git_blob_sha"]==F["v5r"][1]
assert a["v6_extension"]["independent_core_verification"]["git_blob_sha"]==F["c"][1]
assert a["v6_extension"]["global_controller"]["git_blob_sha"]=="211a34f2bc22f531b895b0c7a26187b176875e9f"
assert a["v6_extension"]["torture_universe"]["git_blob_sha"]=="86a7796f2a08e63e0d073cae8bc7a6b66febe98b"
assert a["adversarial_coverage"]["finite_generated_case_count"]==4096
assert a["adversarial_coverage"]["coverage"]==1.0
assert a["adversarial_coverage"]["open_world_recall_claim"] is False
pol=set(a["mandatory_global_policy"])
for x in [
 "PREFER_AUTHORITATIVE_BOUNDED_ENUMERATION_OVER_KEYWORD_GUESSING_WHEN_SUCH_AN_INTERFACE_EXISTS",
 "DISCOVERED_CANDIDATES_ARE_MONOTONIC__RERANKING_MAY_CHANGE_PRIORITY_BUT_MUST_NOT_DELETE_OR_DEACTIVATE_DISCOVERED_IDENTITIES",
 "CHANNELS_SHARING_AN_UPSTREAM_INDEX_OR_PROVIDER_ARE_DISCOUNTED_AS_CORRELATED",
 "OPEN_WORLD_NO_RESULT_REMAINS_UNKNOWN__NEVER_NONEXISTENT",
 "EVERY_REAL_FALSE_NEGATIVE_OR_NEW_FAILURE_CLASS_BECOMES_A_PERMANENT_TORTURE_UNIVERSE_REGRESSION_CASE"
]: assert x in pol,x
assert a["search_engine_strategy"]["selected_architecture"].startswith("BRAIN_OWNED_RETRIEVAL_CONTROLLER")
assert a["incremental_spend_usd"]==0
assert a["acceptance_credit_delta"]==0 and a["family_credit_delta"]==0 and a["capability_credit_delta"]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V6_ACTIVATION_VERIFIED")
