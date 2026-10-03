#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
P=R/"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json"
A=R/"canonical/governance/GLOBAL_RETRIEVAL_V10_ROUTE_STRATEGY_ACTIVATION_V1.json"
AV=R/"canonical/verification/GLOBAL_RETRIEVAL_V10_ROUTE_STRATEGY_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
CV=R/"canonical/verification/GLOBAL_RETRIEVAL_V10_CURRENT_POINTER_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
assert blob(P)=="d2f2ff3d632ab39d83f7697ecf8916690fb643c9",blob(P)
assert blob(A)=="7682e239cd5e0f0ce87a3e66e2584f6e1de3aa3d",blob(A)
assert blob(AV)=="ac18bbb04e9177c764ab91f34396d28280dca8b2",blob(AV)
assert blob(CV)=="56e9f9305cbc2d73ee592911154290bf9fa511c0",blob(CV)
p=json.loads(P.read_text());av=json.loads(AV.read_text());cv=json.loads(CV.read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V10_ENTRYPOINT_V3_BOUND__V8_V9_REGRESSIONS_PRESERVED__ZERO_CREDIT"
x=p["v10_route_strategy_extension"]
assert x["activation_git_blob_sha"]=="7682e239cd5e0f0ce87a3e66e2584f6e1de3aa3d"
assert x["activation_verification_git_blob_sha"]=="ac18bbb04e9177c764ab91f34396d28280dca8b2"
assert x["controller_v3_git_blob_sha"]=="44cb29b284f7ff069a68bf21e221f15d17ee94fa"
assert x["entrypoint_v3_git_blob_sha"]=="f4af9c9c11b84371fd9fde751e7f0ddd56a9148d"
assert x["calibration_v2_git_blob_sha"]=="018f859959d4a15540e8ee1428f6d3e60fe32d11"
assert x["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert x["best_known_live_labeled_case_count"]==13
assert x["best_known_live_hit_count"]==13
assert x["best_known_live_miss_count"]==0
assert x["best_known_live_hit_rate"]==1.0
assert x["open_world_recall_claim"] is False
assert p["v9_generated_stress_extension"]["generated_case_count"]==768
assert p["v9_generated_stress_extension"]["finite_hidden_witness_recall"]==1
assert p["v8_empirical_extension"]["real_hidden_witness_regression"]["monotonic_pooled_top5_recall"]==1
assert p["v10_current_pointer_candidate_verification"]["git_blob_sha"]=="56e9f9305cbc2d73ee592911154290bf9fa511c0"
assert p["v10_current_pointer_candidate_verification"]["conclusion"]=="success"
assert av["independent_runner"]["conclusion"]=="success"
assert cv["independent_runner"]["conclusion"]=="success"
assert "BEST_KNOWN_13_OF_13_LIVE_UNION_IS_FINITE_REGRESSION_TRUTH_NOT_OPEN_WORLD_COMPLETENESS" in p["hard_rules"]
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V10_CURRENT_POINTER_FINAL_STATIC_VERIFIED")
