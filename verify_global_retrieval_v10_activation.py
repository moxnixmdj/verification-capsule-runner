#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/retrieval_v10_activation.json","7682e239cd5e0f0ce87a3e66e2584f6e1de3aa3d"),
 "p":("subjects/retrieval_current_pointer_v9.json","cb58ff10b7c3ac99da8cbee7b8aa0b76006f8dfe"),
 "v9":("subjects/retrieval_v9_activation.json","aa13e5b42b71430e17402893c70cabced5dcfa76"),
 "v9r":("subjects/retrieval_v9_activation_receipt.json","2ba0906603e02b9bba6fdfa2575bcd853e4d3534"),
 "v10r":("subjects/retrieval_v10_controller_receipt.json","83f5e4b28d9b79442a08d1ac22170cfb66c0339c"),
 "opt":("subjects/retrieval_v10_optimized_receipt.json","d5749adf946da6d938b4b1e1baae4b80296b2adf"),
 "bridge":("subjects/retrieval_v10_cross_bridge_receipt.json","f0822d86a544956f686cb491672f4ccc6e399367"),
 "pkg":("subjects/retrieval_v10_package_bridges.json","f4dbf72a918e5ad8ab4618785e2d013c46419a7d"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
a=load("a");p=load("p");v9=load("v9");v9r=load("v9r");v10r=load("v10r");opt=load("opt");br=load("bridge");pkg=load("pkg")
assert a["base_current_authority"]["git_blob_sha"]==F["p"][1]
assert a["base_v9"]["activation_git_blob_sha"]==F["v9"][1]
assert a["base_v9"]["verification_git_blob_sha"]==F["v9r"][1]
assert v9r["independent_runner"]["conclusion"]=="success"
assert a["v10_live_route_strategy"]["controller_verification_git_blob_sha"]==F["v10r"][1]
assert v10r["independent_runner"]["conclusion"]=="success"
assert v10r["verified"]["best_known_live_labeled_case_count"]==13
assert v10r["verified"]["best_known_live_hit_case_count"]==13
assert v10r["verified"]["best_known_live_miss_case_count"]==0
assert v10r["verified"]["best_known_live_hit_rate"]==1.0
assert opt["independent_runner"]["conclusion"]=="success"
assert opt["measured"]["task_count"]==15
assert opt["measured"]["target_hit_count"]==11
assert abs(opt["measured"]["target_recall_on_successful_tasks"]-0.7333333333333333)<1e-12
assert abs(opt["comparison_to_raw_v1"]["relative_recall_multiplier"]-5.133333333333333)<1e-12
assert br["independent_runner"]["conclusion"]=="success"
assert br["measured"]["case_count"]==5 and br["measured"]["target_repo_hit_count"]==4
assert pkg["verified_bridge_count"]==2
m=a["measured_live_truth"]
assert m["best_known_labeled_case_count"]==13 and m["best_known_strategy_union_hit_count"]==13 and m["best_known_strategy_union_miss_count"]==0
assert m["optimized_single_strategy_task_count"]==15 and m["optimized_single_strategy_hit_count"]==11
assert m["cross_ecosystem_repo_bridge_case_count"]==5 and m["cross_ecosystem_repo_bridge_hit_count"]==4
assert m["verified_repository_to_package_bridge_count"]==2
assert m["deep_window_50_case_count"]==5 and m["deep_window_50_hit_count"]==1
pol=set(a["mandatory_policy"])
for x in (
 "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V3",
 "PROVIDER_ROUTE_AND_QUERY_STRATEGY_ARE_JOINT_CALIBRATION_IDENTITIES",
 "PROVIDER_ONLY_PERFORMANCE_CALIBRATION_IS_FORBIDDEN",
 "UNKNOWN_ROUTE_STRATEGIES_USE_EXPLICIT_JEFFREYS_COLD_START",
 "MORE_QUERIES_OR_DEEPER_WINDOWS_ARE_NOT_ASSUMED_BETTER_WITHOUT_MEASURED_RECOVERY",
 "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
): assert x in pol,x
assert "NO_OPEN_WORLD_COMPLETENESS_CLAIM" in a["hard_nonclaims"]
assert "NO_CLAIM_13_LABELED_LIVE_CASES_REPRESENT_ALL_DOMAINS_PROVIDERS_LANGUAGES_OR_FAILURE_CLASSES" in a["hard_nonclaims"]
assert a["incremental_spend_usd"]==0
assert a["acceptance_credit_delta"]==0 and a["family_credit_delta"]==0 and a["capability_credit_delta"]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V10_ACTIVATION_VERIFIED")
