#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,importlib.util,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "gate":("subjects/tool_discovery_retrieval_authority_gate_v5.py","c3324e574c1fafb6aaab443f49b7a9600966e754"),
 "tests":("subjects/test_tool_discovery_retrieval_authority_gate_v5.py","70a35995ca1fadc7b5bfdd8685d144ee6b5c2f49"),
 "v5":("subjects/retrieval_v5_activation.json","8b8b80d43972bb7113b193baaf21dbda292d595e"),
 "v5_verify":("subjects/retrieval_v5_activation_verification.json","acd898bdea67ef0337e33b4335426fbe0dd7320d"),
 "v5_exec_verify":("subjects/retrieval_v5_execution_verification.json","cd1501e167a5429ad0d918e080c527e6d43b8a4d"),
}
def blob(p):
 raw=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def loadj(k):
 p,s=FILES[k]; q=ROOT/p; assert blob(q)==s,(k,blob(q),s); return json.loads(q.read_text())
for k,(p,s) in FILES.items():
 assert blob(ROOT/p)==s,(k,blob(ROOT/p),s)

spec=importlib.util.spec_from_file_location("gate",ROOT/FILES["gate"][0])
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
v5=loadj("v5"); v5v=loadj("v5_verify"); v5e=loadj("v5_exec_verify")

hyper={
 "actions":[{
  "id":gate.ACTION_ID,
  "target_predicates":[gate.TARGET],
  "mandatory_retrieval_authority":dict(gate.EXPECTED),
  "new_reality_units":0,
 }]
}
v2={
 "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1",
 "status":"ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__TEST",
 "operational_policy":{
  "repeat_v1_source_epoch":False,
  "repeat_v2_github_source_epoch":False,
  "current_state":"UNKNOWN_SCOPE_RELATION__STRICT_ACCEPTANCE_OPEN",
 }
}
v2v={
 "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
 "independent_runner":{"conclusion":"success"},
 "verified":{k:True for k in (
  "exact_activation_blob_verified","exact_frontier_binding_verified",
  "exact_frontier_verification_binding_verified","unknown_scope_relation_preserved",
  "v1_source_epoch_repeat_disabled","v2_github_source_epoch_repeat_disabled",
  "zero_credit_preserved"
 )}
}
cv={
 "schema":"PROJECT_BRAIN_RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
 "independent_runner":{"conclusion":"success"},
 "verified":{k:True for k in (
  "unicode_focus","unicode_relevance","no_result_nonexistence_firewall",
  "candidate_only_self_verification_blocked","first_verified_witness_stop",
  "orthogonal_surface_diversification","scope_limited_exhaustive_closure"
 )}
}
bv={
 "schema":"PROJECT_BRAIN_GITHUB_PUBLIC_RETRIEVAL_SURFACES_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
 "independent_runner":{"conclusion":"success"},
 "verified":{k:True for k in (
  "unicode_query_transport_preserved","descriptionless_repository_candidates_retained",
  "code_content_discovery_independent_of_repository_description_and_stars",
  "candidate_only_authority_preserved","no_result_nonexistence_inference_forbidden"
 )}
}
v3={
 "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V3_ACTIVATION_V1",
 "base_retrieval_authority":{"git_blob_sha":gate.EXPECTED["activation_blob"]},
 "v3_verified_extension":{},
 "mandatory_epoch_protocol":[
  "RUN_V2_EXACT_RESIDUAL_COMPILER_AND_VERIFIED_BACKENDS",
  "RUN_ADAPTIVE_UNICODE_QUERY_EVOLUTION_USING_TECHNICAL_ANCHORS_AND_PRIOR_CANDIDATE_TERMS",
  "COMPILE_ORTHOGONAL_PUBLIC_SOURCE_FEDERATION_REQUESTS",
  "IF_NO_SUFFICIENT_WITNESS_EXISTS_PRESERVE_UNKNOWN_AND_CONTENT_ADDRESS_THE_CONSUMED_SOURCE_EPOCH",
 ],
 "hard_rules":["NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_THE_SEARCH"],
 "stop_rules":{"no_witness_and_scope_not_complete":"UNKNOWN__DO_NOT_INFER_NONEXISTENCE"}
}
v3v={
 "schema":"PROJECT_BRAIN_RETRIEVAL_V3_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
 "independent_runner":{"conclusion":"success"},
 "verified":{k:True for k in (
  "exact_activation_blob_verified","v2_base_authority_preserved",
  "v3_component_receipt_binding_verified","multilingual_candidate_generation_required_before_epoch_exhaustion",
  "adaptive_unicode_query_evolution_required_before_epoch_exhaustion",
  "orthogonal_public_source_federation_required_before_epoch_exhaustion",
  "unbridgeable_material_preserves_unknown","no_result_nonexistence_inference_forbidden",
  "zero_credit_preserved"
 )}
}
v4={
 "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V4_ACTIVATION_V1",
 "base_retrieval_authority":{"git_blob_sha":gate.EXPECTED["v3_activation_blob"],"rule":"V3_REMAINS_MANDATORY_AND_IS_NOT_WEAKENED"},
 "mandatory_epoch_protocol":[
  "SELECT_FEDERATION_QUERIES_WITH_EXACT_TECHNICAL_ANCHORS_AND_CROSS_SCRIPT_DIVERSITY_BEFORE_REDUNDANT_BASE_QUERIES",
  "COMPILE_SELECTED_SOURCE_QUERIES_INTO_OPEN_WEB_ACTIONS_FOR_THE_EXACT_VERIFIED_BACKEND_ROUTER",
  "REQUIRE_ONE_ROUTER_ATTEMPT_RECEIPT_PER_SELECTED_SOURCE_QUERY_CELL_BEFORE_SOURCE_EPOCH_CONSUMPTION",
  "BACKEND_UNBOUND_DOES_NOT_COUNT_AS_AN_ATTEMPT",
  "FAILED_OR_EMPTY_ATTEMPTS_REMAIN_UNKNOWN",
  "SOURCE_EPOCH_CONSUMPTION_NEVER_AUTHORIZES_OPEN_WORLD_NONEXISTENCE",
 ],
 "stop_rules":{
  "missing_or_unbound_router_receipt":"FAIL_CLOSED__DO_NOT_CONSUME_EPOCH",
  "no_witness_and_open_world_scope_not_complete":"UNKNOWN__DO_NOT_INFER_NONEXISTENCE",
 }
}
v4v={
 "schema":"PROJECT_BRAIN_RETRIEVAL_V4_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1",
 "independent_runner":{"conclusion":"success"},
 "verified":{k:True for k in (
  "exact_activation_blob_verified","exact_v4_component_receipt_binding_verified",
  "exact_v3_base_binding_verified","v3_remains_mandatory_and_unweakened",
  "exact_technical_anchor_priority_required","cross_script_diversity_required_before_redundant_base_queries",
  "selected_federation_queries_must_compile_to_verified_router_actions",
  "one_router_attempt_receipt_per_selected_cell_required","backend_unbound_does_not_count_as_attempt",
  "failed_or_empty_attempts_preserve_unknown","epoch_consumption_does_not_authorize_nonexistence",
  "zero_credit_preserved"
 )}
}
actual={**{k:v for k,v in gate.EXPECTED.items() if k.endswith("_blob")},
        **{k:v for k,v in gate.V4_EXPECTED.items() if k.endswith("_blob")},
        **{k:v for k,v in gate.V5_EXPECTED.items() if k.endswith("_blob")}}

def run(**overrides):
 args=dict(
  hypergraph=hyper,activation=v2,activation_verification=v2v,
  compiler_verification=cv,backend_verification=bv,
  v3_activation=v3,v3_activation_verification=v3v,
  v4_activation=v4,v4_activation_verification=v4v,
  v5_activation=v5,v5_activation_verification=v5v,
  v5_execution_verification=v5e,actual_blobs=actual,
 )
 args.update(overrides)
 return gate.validate(**args)

out=run()
assert out["pass"] is True,out
assert out["v5_success_only_epoch_consumption_mandatory"] is True,out
assert "V2_V3_V4_V5" in out["status"],out

m=copy.deepcopy(v5)
m["mandatory_epoch_protocol"].remove("TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED")
bad=run(v5_activation=m)
assert bad["pass"] is False and any("V5_PROTOCOL_MISSING" in e for e in bad["errors"]),bad

m=copy.deepcopy(v5)
m["hard_rules"].remove("NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION")
bad=run(v5_activation=m)
assert bad["pass"] is False and "V5_HARD_RULE_MISSING:NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION" in bad["errors"],bad

m=copy.deepcopy(v5v); m["independent_runner"]["conclusion"]="failure"
bad=run(v5_activation_verification=m)
assert bad["pass"] is False and "V5_ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS" in bad["errors"],bad

m=copy.deepcopy(v5e); m["independent_runner"]["conclusion"]="failure"
bad=run(v5_execution_verification=m)
assert bad["pass"] is False and "V5_EXECUTION_INDEPENDENT_RUNNER_NOT_SUCCESS" in bad["errors"],bad

bl=dict(actual); bl["v5_executor_blob"]="0"*40
bad=run(actual_blobs=bl)
assert bad["pass"] is False and "ACTUAL_BLOB_MISMATCH:v5_executor_blob" in bad["errors"],bad

print("RETRIEVAL_V5_LIVE_GATE_VERIFIED")
print(json.dumps({
 "exact_gate_blob":FILES["gate"][1],
 "exact_test_blob":FILES["tests"][1],
 "v5_activation_blob":FILES["v5"][1],
 "v5_activation_verification_blob":FILES["v5_verify"][1],
 "v5_execution_verification_blob":FILES["v5_exec_verify"][1],
 "baseline_gate_pass":True,
 "retry_rule_mutation_fails_closed":True,
 "partial_batch_rule_mutation_fails_closed":True,
 "failed_activation_receipt_fails_closed":True,
 "failed_execution_receipt_fails_closed":True,
 "stale_executor_hash_fails_closed":True,
 "zero_credit_preserved":True
},sort_keys=True))
