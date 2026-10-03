#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "v2":("subjects/brain_tool_discovery_frontier_v2.json","854dd675f8454be9e0ac9316fac3eefe407305c0"),
 "intent":("subjects/brain_tool_discovery_frontier_v2_intent.json","0ef5bcced2fa6d8a47efb94706534eefc73f5704"),
 "provider":("subjects/brain_github_retrieval_verification.json","ca5acd7afbf14b7cce568ec482c160c3795e57ba"),
 "wake":("subjects/brain_tool_discovery_github_wake.json","1bac16bdbceebe49c949c06e097652669d7e4314"),
 "v1":("subjects/brain_tool_discovery_frontier_v1.json","5a7a2ddf2bb36b2b2ef8e01189d09550a7304e4a"),
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(key):
 path,sha=FILES[key]
 p=ROOT/path
 assert blob(p)==sha,(key,blob(p),sha)
 return json.loads(p.read_text())

v2=load("v2"); intent=load("intent"); provider=load("provider"); wake=load("wake"); v1=load("v1")

assert v2["supersedes_frontier"]["git_blob_sha"]==FILES["v1"][1]
assert v2["new_source_epoch"]["provider_verification"]["git_blob_sha"]==FILES["provider"][1]
assert v2["new_source_epoch"]["wake_execution"]["git_blob_sha"]==FILES["wake"][1]
assert provider["independent_runner"]["conclusion"]=="success"
assert provider["verified"]["unicode_query_transport_preserved"] is True
assert provider["verified"]["code_content_discovery_independent_of_repository_description_and_stars"] is True
assert provider["capability_credit_delta"]==0 and provider["family_credit_delta"]==0

r=v2["residual_state_after_wake"]
assert r["scope_complete_proof_found"] is False
assert r["admissible_opus55_matched_trajectory_or_harness_receipt_found"] is False
assert r["opus55_valid_route_top1_comparator_found"] is False
assert r["scope_relation_closed"] is False
assert r["strict_acceptance_closed"] is False
assert r["state"]=="UNKNOWN__NOT_NONEXISTENCE"
assert len(r["remaining_minimum_residual"])==2

policy=v2["search_policy"]
assert policy["repeat_v1_source_set"] is False
assert policy["repeat_github_code_history_epoch_recorded_here"] is False
assert policy["candidate_derivative_sources_do_not_reopen_search"] is True
assert policy["next_action_without_wake"].startswith("DO_NOT_SPEND_ADDITIONAL_RETRIEVAL_ACTIONS")

assert "NO_RESULT_IS_NOT_NONEXISTENCE" in v2["hard_rules"]
assert "NO_FINITE_GITHUB_QUERY_SET_TO_GLOBAL_COMPLETENESS_INFERENCE" in v2["hard_rules"]
assert v2["capability_credit_delta"]==0 and v2["family_credit_delta"]==0
assert v2["execution_authority"] is False and v2["promotion_authority"] is False

wd=wake["deduction"]
assert wd["new_admissible_scope_complete_witness"] is False
assert wd["new_admissible_opus55_matched_trajectory_receipt"] is False
assert wd["new_valid_route_top1_comparator"] is False
assert wd["state"]=="UNKNOWN__DO_NOT_INFER_NONEXISTENCE"
assert wd["repeat_same_github_source_epoch"] is False
assert len(wake["candidate_dispositions"])==4
assert all("disposition" in x and "basis" in x for x in wake["candidate_dispositions"])
assert "NO_GLOBAL_NONEXISTENCE_CLAIM" in wake["hard_nonclaims"]

assert intent["target_predicate"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
assert "ZERO_IMMEDIATE_ACCEPTANCE_DELTA" in intent["expected_terminal_delta"]
assert intent["capability_credit_delta"]==0 and intent["family_credit_delta"]==0

# V2 must preserve the same exact residual as V1 rather than silently weakening it.
v1_res=v1["residual_epoch"]["semantic_state"]["remaining_minimum_residual"]
assert r["remaining_minimum_residual"]==v1_res,(r["remaining_minimum_residual"],v1_res)

print("TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "unknown_preserved":True,
 "same_residual_preserved":True,
 "github_epoch_consumed_once":True,
 "zero_credit_preserved":True
},sort_keys=True))
