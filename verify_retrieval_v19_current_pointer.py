#!/usr/bin/env python3
import json,pathlib
R=pathlib.Path(__file__).resolve().parent
p=json.loads((R/"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json").read_text())
v=json.loads((R/"canonical/verification/RETRIEVAL_V19_ROUTE_PORTFOLIO_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
assert p["status"]=="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__GLOBAL_RETRIEVAL_V6_CURRENT__EMPIRICAL_V10_RANKER__V18_FINITE_LIVE_30_OF_30__V19_ENTRYPOINT_V4_BOUND__ZERO_CREDIT"
x=p["v19_verified_route_portfolio"]
assert x["portfolio_git_blob_sha"]=="855a6cba59fff8c079f61212acadc254c4e9e736"
assert x["entrypoint_v4_git_blob_sha"]=="2ad2fb952b3c361e74cb083b335d39b04a7c130b"
assert x["verification_git_blob_sha"]=="4604a93bf220edcf9691ad9cb059df38f8674c48"
assert x["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert x["answer_key_identity_permitted"] is False
assert p["v10_route_strategy_extension"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is False
assert p["v10_route_strategy_extension"]["controller_v3_remains_underlying_ranker"] is True
assert v["independent_runner"]["conclusion"]=="success"
assert v["verified"]["version_line_history_identity_bridge_generic"] is True
assert "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V4" in p["hard_rules"]
assert "FRESH_HOLDOUT_MEASUREMENT_MUST_USE_THE_FROZEN_ENTRYPOINT_V4_BYTES_WITHOUT_POST_HOC_ROUTE_CHANGES" in p["hard_rules"]
assert p["execution_authority"] is False and p["promotion_authority"] is False
print("RETRIEVAL_V19_CURRENT_POINTER_VERIFIED")
