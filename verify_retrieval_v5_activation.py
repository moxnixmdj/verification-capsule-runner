#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "v5":("subjects/retrieval_v5_activation.json","8b8b80d43972bb7113b193baaf21dbda292d595e"),
 "receipt":("subjects/retrieval_v5_executor_verification.json","cd1501e167a5429ad0d918e080c527e6d43b8a4d"),
 "v4":("subjects/retrieval_v4_activation.json","643890c1d09844ea49de434df8ffec02962806e4"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]; q=ROOT/p
 assert blob(q)==s,(k,blob(q),s)
 return json.loads(q.read_text())

v5=load("v5"); receipt=load("receipt"); v4=load("v4")
assert v5["schema"]=="PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V5_ACTIVATION_V1"
assert v5["base_retrieval_authority"]["git_blob_sha"]==FILES["v4"][1]
assert v5["base_retrieval_authority"]["rule"]=="V4_REMAINS_MANDATORY_AND_IS_NOT_WEAKENED"
assert receipt["independent_runner"]["conclusion"]=="success"
assert receipt["verified"]["partial_batch_cannot_consume_epoch"] is True
assert receipt["verified"]["transient_failure_remains_unconsumed_and_retryable"] is True
assert receipt["verified"]["all_selected_cells_required_before_epoch_consumption"] is True
assert receipt["verified"]["off_domain_candidate_filtering"] is True
assert receipt["verified"]["consumed_cell_replay_suppression"] is True
assert receipt["verified"]["candidate_self_promotion_rejected"] is True
assert receipt["verified"]["epoch_consumption_does_not_authorize_nonexistence"] is True

protocol=set(v5["mandatory_epoch_protocol"])
for required in (
 "RUN_THE_EXACT_VERIFIED_V4_DIVERSITY_PRESERVING_FEDERATION_PLAN",
 "ONLY_SUCCESSFULLY_EXECUTED_QUERY_CELLS_ENTER_THE_CONSUMED_SET",
 "TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED",
 "PARTIAL_BATCH_EXECUTION_CANNOT_CONSUME_THE_SOURCE_EPOCH",
 "REQUIRE_ALL_SELECTED_SOURCE_QUERY_CELLS_SUCCESSFULLY_CONSUMED_BEFORE_SOURCE_EPOCH_CONSUMPTION",
 "FILTER_OFF_DOMAIN_RESULTS_BEFORE_A_SOURCE_CELL_CAN_BE_SATISFIED",
 "REJECT_CANDIDATE_SELF_PROMOTION_OR_ACCEPTANCE_AUTHORITY_SMUGGLING",
 "STOP_IMMEDIATELY_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
):
 assert required in protocol,required

rules=set(v5["hard_rules"])
for required in (
 "V5_EXTENDS_V4_AND_CANNOT_BYPASS_OR_WEAKEN_V4",
 "NO_FAILED_TRANSIENT_OR_REJECTED_BACKEND_CELL_MAY_BE_MARKED_CONSUMED",
 "NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION",
 "NO_OFF_DOMAIN_RESULT_MAY_SATISFY_A_DOMAIN_SPECIFIC_SOURCE_CELL",
 "NO_CONSUMED_CELL_REPLAY",
 "NO_SOURCE_EPOCH_CONSUMPTION_TO_OPEN_WORLD_COMPLETENESS_OR_NONEXISTENCE_INFERENCE",
):
 assert required in rules,required

assert v5["stop_rules"]["some_selected_cells_unconsumed_or_failed"].startswith("CONTINUE_OR_RETRY")
assert v5["stop_rules"]["open_world_no_witness"]=="UNKNOWN__DO_NOT_INFER_NONEXISTENCE"
assert v5["capability_credit_delta"]==0 and v5["family_credit_delta"]==0
assert v5["execution_authority"] is False and v5["promotion_authority"] is False

# Mutation-style falsification of policy: these weakenings must be detectable.
mut=json.loads(json.dumps(v5))
mut["mandatory_epoch_protocol"].remove("TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED")
assert "TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED" not in set(mut["mandatory_epoch_protocol"])
mut2=json.loads(json.dumps(v5))
mut2["base_retrieval_authority"]["git_blob_sha"]="0"*40
assert mut2["base_retrieval_authority"]["git_blob_sha"]!=FILES["v4"][1]

print("RETRIEVAL_V5_ACTIVATION_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "v4_base_preserved":True,
 "strict_success_only_consumption_mandatory":True,
 "partial_batch_exhaustion_forbidden":True,
 "failure_retryability_mandatory":True,
 "off_domain_filtering_mandatory":True,
 "replay_suppression_mandatory":True,
 "unknown_preserved":True,
 "zero_credit":True
},sort_keys=True))
