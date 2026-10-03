#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
base=json.loads((ROOT/"CURRENT_TERMINAL_AUTHORITY_BASE_V1.json").read_text())
new=json.loads((ROOT/"CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())

assert base["truth"]==new["truth"],(base["truth"],new["truth"])
assert new["truth"]["opus55_acceptance"]=="3/19_PASS__16/19_OPEN",new["truth"]
assert new["truth"]["achieved"] is False,new["truth"]
assert base["next_terminal_action"]==new["next_terminal_action"],(
    base["next_terminal_action"],new["next_terminal_action"]
)

expected_control={
    "contract_path":"canonical/governance/RESIDUAL_WITNESS_RETRIEVAL_CONTRACT_V1.json",
    "contract_git_blob_sha":"9c3098454d9c577cd92b020bdc2de157e8c626e9",
    "runtime_path":"canonical/runtime/residual_witness_retrieval_compiler_v1.py",
    "runtime_git_blob_sha":"9daa8d590f3356b3fc51eccf75c56cbf515239e4",
    "verification_path":"canonical/verification/RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "verification_git_blob_sha":"f0a68c8219d704875535543060f63b9ecaca6dd5",
    "status":"ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__UNICODE_BEHAVIORAL_QUERY_LATTICE__NO_RESULT_NONEXISTENCE_FIREWALL__SCOPE_LIMITED_EXHAUSTIVE_CLOSURE__ZERO_CREDIT",
}
expected_router={
    "contract_path":"canonical/governance/RESIDUAL_WITNESS_BACKEND_CONTRACT_V1.json",
    "contract_git_blob_sha":"97acb0d74848230df2deeed0b6902186087c12b5",
    "runtime_path":"canonical/runtime/residual_witness_backend_router_v1.py",
    "runtime_git_blob_sha":"8935439e587fb723a4464fe9a15e8772ddb076bf",
    "verification_path":"canonical/verification/RESIDUAL_WITNESS_BACKEND_ROUTER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "verification_git_blob_sha":"34512250b7bc7a69a03ab7d4e9b4d1ef4d2c8bfc",
    "status":"ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__CANDIDATE_SUFFICIENCY_FIREWALL__BACKEND_AUTHORITY_SEPARATION__ZERO_CREDIT",
}
assert new["sources"]["residual_witness_retrieval_control"]==expected_control,new["sources"]["residual_witness_retrieval_control"]
assert new["sources"]["residual_witness_backend_router"]==expected_router,new["sources"]["residual_witness_backend_router"]

retrieval=new["residual_witness_retrieval"]
assert retrieval["status"]=="ACTIVE_VERIFIED_CONTROL_PLANE__LIVE_ACCEPTANCE_CREDIT_REQUIRES_INDEPENDENT_SUFFICIENT_WITNESS",retrieval
assert retrieval["current_acceptance_preserved"]=="3_OF_19__8_OF_38",retrieval
assert retrieval["capability_credit_delta"]==0,retrieval
assert retrieval["family_credit_delta"]==0,retrieval
assert retrieval["execution_authority"] is False,retrieval
assert retrieval["promotion_authority"] is False,retrieval
live=retrieval["current_tool_discovery_live_application"]
assert live["retrieval_result"]=="NO_NEW_ADMISSIBLE_WITNESS_FROM_CURRENT_OFFICIAL_PUBLIC_SOURCE_SURFACES",live
assert live["boundary"]=="BOUNDED_SEARCH_RESULT_ONLY__NOT_GLOBAL_NONEXISTENCE",live
assert set(live["preserved_open_facts"])=={
    "SAME_HARNESS_AND_COMMON_TOOL_AUTHORITY_COMPARABILITY",
    "VALID_ROUTE_TOP1_OPUS55_COMPARATOR",
},live

# Strong semantic-diff proof: after removing exactly the intended additions,
# the reconciled authority must equal the pre-reconciliation authority.
stripped=copy.deepcopy(new)
stripped.pop("residual_witness_retrieval",None)
stripped["sources"].pop("residual_witness_retrieval_control",None)
stripped["sources"].pop("residual_witness_backend_router",None)
assert stripped==base,"UNINTENDED_AUTHORITY_MUTATION"

print(json.dumps({
    "status":"PASS",
    "acceptance_preserved":new["truth"]["opus55_acceptance"],
    "next_terminal_action_preserved":True,
    "semantic_diff_only_expected_additions":True,
    "retrieval_controls_reconciled":True,
    "bounded_unknown_preserved":True,
},sort_keys=True))
