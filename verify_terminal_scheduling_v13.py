#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "candidate":("subjects/terminal_scheduling_v13_candidate.json","2b597ea1840196623a2d7e31f9c613cd993ec6ba"),
 "v12v":("subjects/terminal_scheduling_v12_verification.json","b075e9f0d97f8d72db7e74bc36bb378e34b8fead"),
 "postv":("subjects/post_dual_frontier_verification.json","f7f60a5932ac305aa0db8aef2643119dd10b33d9"),
 "v5v":("subjects/retrieval_v5_activation_verification_v13.json","acd898bdea67ef0337e33b4335426fbe0dd7320d"),
 "v5e":("subjects/retrieval_v5_execution_verification_v13.json","cd1501e167a5429ad0d918e080c527e6d43b8a4d"),
 "v5live":("subjects/retrieval_v5_live_gate_verification_v13.json","aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b"),
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(k):
 p,s=FILES[k]; q=ROOT/p
 actual=blob(q); assert actual==s,(k,actual,s)
 return json.loads(q.read_text(encoding="utf-8"))
for k,(p,s) in FILES.items():
 assert blob(ROOT/p)==s,(k,blob(ROOT/p),s)

cand=load("candidate"); v12v=load("v12v"); postv=load("postv")
v5v=load("v5v"); v5e=load("v5e"); v5live=load("v5live")

EXPECTED_DIRECT=["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
TRUE_RETRIEVAL=[
 "mandatory",
 "strict_success_only_source_cell_consumption_required",
 "transient_failures_retryable_and_unconsumed",
 "all_selected_cells_required_before_epoch_consumption",
]
FALSE_RETRIEVAL=[
 "partial_batch_epoch_consumption_allowed",
 "off_domain_result_may_satisfy_source_cell",
 "consumed_cell_replay_allowed",
 "empty_or_failed_attempt_proves_nonexistence",
]
TRUE_POLICY=[
 "run_all_31_zero_reality_work_units_concurrently",
 "matched_16_child_facts_first_resource_priority_without_serializing_siblings",
 "fixed_point_after_every_independently_verified_delta",
 "recompute_frontier_after_every_verified_delta",
 "cancel_newly_dominated_branches",
 "ownership_reconciliation_parallel_with_acceptance",
]
REQUIRED_RULES=[
 "PRESERVE_4_OF_19_ACCEPTANCE_AND_11_OF_38_ATOMIC_PROOF_COUNTS",
 "TOOL_DISCOVERY_LIVE_RETRIEVAL_MUST_USE_EXACT_VERIFIED_V5_OVER_V4_OVER_V3_OVER_V2_CHAIN",
 "ONLY_SUCCESSFULLY_EXECUTED_SOURCE_CELLS_MAY_BE_CONSUMED",
 "TRANSIENT_OR_REJECTED_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED",
 "NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION",
 "NO_OFF_DOMAIN_RESULT_MAY_SATISFY_A_DOMAIN_SPECIFIC_SOURCE_CELL",
 "NO_REPLAY_OF_CONSUMED_SOURCE_CELLS",
 "NO_RESULT_IS_NOT_NONEXISTENCE",
 "NO_FRESH_REALITY_UNTIL_ZERO_REALITY_FIXED_POINT",
 "NO_ACCEPTANCE_CAPABILITY_FAMILY_OR_OWNERSHIP_CREDIT_FROM_SCHEDULING",
]

def validate(c):
 errors=[]
 if c.get("schema")!="PROJECT_BRAIN_TERMINAL_SCHEDULING_V13_ACTIVE_AUTHORITY_CANDIDATE_V1":
  errors.append("SCHEMA")
 live=c.get("live_world") or {}
 if (
  live.get("registry_predicates"),live.get("proved_predicates"),live.get("unresolved_predicates"),
  live.get("opus55_acceptance"),live.get("active_zero_reality_requirements"),
  live.get("active_nondominated_certificates"),live.get("zero_reality_covered_predicates"),
  live.get("primitive_zero_reality_work_units"),live.get("matched_priority_child_facts")
 )!=(38,11,27,"4/19_PASS__15/19_OPEN",17,14,25,31,16):
  errors.append("LIVE_WORLD")
 if live.get("direct_reality_blocked_predicates")!=EXPECTED_DIRECT:
  errors.append("DIRECT_REALITY")
 basis=c.get("authority_basis") or {}
 exact={
  "v12_independent_verification":"b075e9f0d97f8d72db7e74bc36bb378e34b8fead",
  "post_dual_frontier_verification":"f7f60a5932ac305aa0db8aef2643119dd10b33d9",
  "retrieval_v5_activation_verification":"acd898bdea67ef0337e33b4335426fbe0dd7320d",
  "retrieval_v5_execution_verification":"cd1501e167a5429ad0d918e080c527e6d43b8a4d",
  "retrieval_v5_live_gate_verification":"aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b",
  "retrieval_gate_runtime":"c3324e574c1fafb6aaab443f49b7a9600966e754",
 }
 for key,sha in exact.items():
  if (basis.get(key) or {}).get("git_blob_sha")!=sha: errors.append("BASIS:"+key)
 r=c.get("mandatory_tool_discovery_retrieval") or {}
 if r.get("authority")!="V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
  errors.append("V5_AUTHORITY")
 if r.get("gate_git_blob_sha")!="c3324e574c1fafb6aaab443f49b7a9600966e754":
  errors.append("GATE_HASH")
 if r.get("v5_activation_verification_git_blob_sha")!="acd898bdea67ef0337e33b4335426fbe0dd7320d":
  errors.append("V5V_HASH")
 if r.get("v5_execution_verification_git_blob_sha")!="cd1501e167a5429ad0d918e080c527e6d43b8a4d":
  errors.append("V5E_HASH")
 if r.get("v5_live_gate_verification_git_blob_sha")!="aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b":
  errors.append("V5LIVE_HASH")
 for k in TRUE_RETRIEVAL:
  if r.get(k) is not True: errors.append("RETRIEVAL_TRUE:"+k)
 for k in FALSE_RETRIEVAL:
  if r.get(k) is not False: errors.append("RETRIEVAL_FALSE:"+k)
 p=c.get("execution_policy") or {}
 for k in TRUE_POLICY:
  if p.get(k) is not True: errors.append("POLICY_TRUE:"+k)
 if p.get("fresh_reality_before_zero_reality_fixed_point") is not False:
  errors.append("FRESH_REALITY_POLICY")
 rules=c.get("hard_rules") or []
 for rule in REQUIRED_RULES:
  if rule not in rules: errors.append("RULE:"+rule)
 for k in ("new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"):
  if c.get(k)!=0: errors.append("NONZERO:"+k)
 for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
  if c.get(k) is not False: errors.append("AUTHORITY:"+k)
 return sorted(set(errors))

assert not validate(cand),validate(cand)

# Independent upstream receipt checks.
assert v12v["independent_runner"]["conclusion"]=="success"
assert v12v["verified"]["active_zero_reality_requirements"]==17
assert v12v["verified"]["primitive_zero_reality_work_units"]==31
assert v12v["verified"]["proved_predicates"]==11
assert v12v["verified"]["unresolved_predicates"]==27
assert postv["independent_runner"]["conclusion"]=="success"
assert postv["verified"]["current_zero_reality_requirements"]==17
assert postv["verified"]["current_nondominated_zero_reality_certificates"]==14
assert postv["verified"]["primitive_zero_reality_work_units"]==31
assert postv["verified"]["current_global_fresh_reality_authority"] is False
assert v5v["independent_runner"]["conclusion"]=="success"
assert v5v["verified"]["strict_success_only_source_cell_consumption_mandatory"] is True
assert v5v["verified"]["transient_failures_retryable_and_unconsumed"] is True
assert v5v["verified"]["partial_batch_epoch_consumption_forbidden"] is True
assert v5e["independent_runner"]["conclusion"]=="success"
assert v5e["verified"]["all_selected_cells_required_before_epoch_consumption"] is True
assert v5e["verified"]["epoch_consumption_does_not_authorize_nonexistence"] is True
assert v5live["independent_runner"]["conclusion"]=="success"
assert v5live["verified"]["v2_v3_v4_v5_chain_passes"] is True
assert v5live["verified"]["v5_success_only_epoch_consumption_mandatory"] is True

# Adversarial mutations must fail closed.
m=copy.deepcopy(cand); m["mandatory_tool_discovery_retrieval"]["transient_failures_retryable_and_unconsumed"]=False
assert "RETRIEVAL_TRUE:transient_failures_retryable_and_unconsumed" in validate(m)
m=copy.deepcopy(cand); m["mandatory_tool_discovery_retrieval"]["partial_batch_epoch_consumption_allowed"]=True
assert "RETRIEVAL_FALSE:partial_batch_epoch_consumption_allowed" in validate(m)
m=copy.deepcopy(cand); m["execution_policy"]["run_all_31_zero_reality_work_units_concurrently"]=False
assert "POLICY_TRUE:run_all_31_zero_reality_work_units_concurrently" in validate(m)
m=copy.deepcopy(cand); m["fresh_reality_authority"]=True
assert "AUTHORITY:fresh_reality_authority" in validate(m)
m=copy.deepcopy(cand); m["hard_rules"].remove("NO_RESULT_IS_NOT_NONEXISTENCE")
assert "RULE:NO_RESULT_IS_NOT_NONEXISTENCE" in validate(m)

print("TERMINAL_SCHEDULING_V13_CANDIDATE_VERIFIED")
print(json.dumps({
 "candidate_blob":FILES["candidate"][1],
 "v12_verification_blob":FILES["v12v"][1],
 "post_dual_verification_blob":FILES["postv"][1],
 "v5_activation_verification_blob":FILES["v5v"][1],
 "v5_execution_verification_blob":FILES["v5e"][1],
 "v5_live_gate_verification_blob":FILES["v5live"][1],
 "live_world":"11_PROVED__27_UNRESOLVED__4_OF_19_ACCEPTANCE",
 "zero_reality":"17_REQUIREMENTS__14_CERTIFICATES__31_PRIMITIVE_WORK_UNITS",
 "retrieval":"STRICT_V5_OVER_V4_OVER_V3_OVER_V2",
 "mutation_fail_closed":True,
 "zero_credit":True,
 "fresh_reality_authority":False
},sort_keys=True))
