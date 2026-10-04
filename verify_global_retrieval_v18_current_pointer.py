#!/usr/bin/env python3
import json,pathlib
R=pathlib.Path(__file__).resolve().parent
p=json.loads((R/"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json").read_text())
a=json.loads((R/"canonical/governance/GLOBAL_RETRIEVAL_V18_LIVE_PROVIDER_EXTENSION_ACTIVATION_V1.json").read_text())
v=json.loads((R/"canonical/verification/GLOBAL_RETRIEVAL_V18_LIVE_PROVIDER_EXTENSION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V10_ENTRYPOINT_V3_BOUND__V18_FINITE_LIVE_30_OF_30_BOUND__ZERO_CREDIT"
x=p["v18_live_provider_extension"]
assert x["activation_git_blob_sha"]=="0e2abcbabb1694624be6d85b3d3894a7c55cfa14"
assert x["verification_git_blob_sha"]=="7944f73cc446a81bffaa9af5c30f1ff943a16e5e"
assert x["conclusion"]=="success"
assert x["finite_live_labeled_case_count"]==30
assert x["finite_live_union_hit_count"]==30
assert x["finite_live_union_miss_count"]==0
assert x["finite_live_union_recall"]==1.0
assert x["open_world_completeness_claim"] is False
assert x["mandatory_regression_only"] is True
assert a["measured_finite_live_truth"]["best_known_union_hit_count"]==30
assert a["measured_finite_live_truth"]["best_known_union_recall"]==1.0
assert v["independent_runner"]["conclusion"]=="success"
assert v["verified"]["v18_union_hits"]==30
assert "CURRENT_V10_ENTRYPOINT_V3_REMAINS_THE_MANDATORY_AUTHORIZED_PLAN_COMPILER_UNTIL_SEPARATELY_SUPERSEDED" in p["hard_rules"]
assert "FINITE_LIVE_30_OF_30_IS_REGRESSION_TRUTH_NOT_OPEN_WORLD_COMPLETENESS" in p["hard_rules"]
assert p["v10_route_strategy_extension"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert p["incremental_spend_usd"]==0
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V18_CURRENT_POINTER_VERIFIED")
