#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "p":("subjects/retrieval_v10_pointer_candidate.json","eb88533398a3c4ecb81a0f87bd2f212348f1b9e9"),
 "a":("subjects/retrieval_v10_activation_for_pointer.json","7682e239cd5e0f0ce87a3e66e2584f6e1de3aa3d"),
 "v":("subjects/retrieval_v10_activation_receipt_for_pointer.json","ac18bbb04e9177c764ab91f34396d28280dca8b2"),
}
def blob(q):
 x=q.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
p=load("p");a=load("a");v=load("v")
assert p["status"]=="ACTIVE_CANDIDATE_POINTER__GLOBAL_RETRIEVAL_V10_ROUTE_STRATEGY_ENTRYPOINT_V3_BOUND__FINAL_POINTER_VERIFICATION_REQUIRED__ZERO_CREDIT"
x=p["v10_route_strategy_extension"]
assert x["activation_git_blob_sha"]==F["a"][1]
assert x["activation_verification_git_blob_sha"]==F["v"][1]
assert x["conclusion"]=="success"
assert x["controller_v3_git_blob_sha"]=="44cb29b284f7ff069a68bf21e221f15d17ee94fa"
assert x["entrypoint_v3_git_blob_sha"]=="f4af9c9c11b84371fd9fde751e7f0ddd56a9148d"
assert x["calibration_v2_git_blob_sha"]=="018f859959d4a15540e8ee1428f6d3e60fe32d11"
assert x["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert x["best_known_live_labeled_case_count"]==13
assert x["best_known_live_hit_count"]==13
assert x["best_known_live_miss_count"]==0
assert x["best_known_live_hit_rate"]==1.0
assert x["open_world_recall_claim"] is False
assert p["v8_empirical_extension"]["live_empirical_routing"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is False
assert p["v8_empirical_extension"]["live_empirical_routing"]["superseded_for_current_plan_compilation_by"]=="canonical/runtime/global_retrieval_entrypoint_v3.py"
assert v["independent_runner"]["conclusion"]=="success"
assert "BEST_KNOWN_13_OF_13_LIVE_UNION_IS_FINITE_REGRESSION_TRUTH_NOT_OPEN_WORLD_COMPLETENESS" in p["hard_rules"]
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V10_CURRENT_POINTER_CANDIDATE_VERIFIED")
