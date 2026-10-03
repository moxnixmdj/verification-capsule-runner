#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "candidate":("subjects/v13_candidate.json","56f8a7fe69ba9123d9e92c107d269aa278a80253"),
 "scheduler":("subjects/current_scheduler.py","9ae2b990578b042dd24074fd5013378b72e64b6b"),
 "gate":("subjects/current_retrieval_gate.py","c3324e574c1fafb6aaab443f49b7a9600966e754"),
 "hypergraph":("subjects/current_hypergraph.json","38b53147597b5457859e3b0d031168842560e3e2"),
 "authority":("subjects/current_terminal_authority.json","f47a69253e7eb75e139b445b736d3d18b33be622"),
 "v12":("subjects/v12_verification.json","86f4ec2da215491bf4de9812cf76e3e1f5120ee2"),
 "v5a":("subjects/v5_activation_verification.json","acd898bdea67ef0337e33b4335426fbe0dd7320d"),
 "v5e":("subjects/v5_execution_verification.json","cd1501e167a5429ad0d918e080c527e6d43b8a4d"),
 "v5g":("subjects/v5_live_gate_verification.json","aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b"),
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def read(k):
 p,sha=FILES[k]; path=ROOT/p
 got=blob(path); assert got==sha,(k,got,sha)
 return path.read_text()
def load(k): return json.loads(read(k))

candidate=load("candidate")
authority=load("authority")
v12=load("v12")
v5a=load("v5a")
v5e=load("v5e")
v5g=load("v5g")
hyper=load("hypergraph")
scheduler=read("scheduler")
gate=read("gate")

# Current authority truth.
assert authority["truth"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert candidate["current_acceptance_authority"]["git_blob_sha"]==FILES["authority"][1]

# Preserve the newest verified scheduling state, but upgrade retrieval authority.
assert v12["independent_runner"]["conclusion"]=="success"
assert v12["verified"]["active_zero_reality_requirements"]==17
assert v12["verified"]["primitive_zero_reality_work_units"]==31
assert candidate["base_scheduling_authority"]["verification_git_blob_sha"]==FILES["v12"][1]
assert candidate["live_world_preserved_from_v12"]["primitive_zero_reality_work_units"]==31
assert candidate["execution_policy_preserved_from_v12"]["run_all_31_zero_reality_work_units_concurrently"] is True

# V5 chain is independently green.
for obj in (v5a,v5e,v5g):
 assert obj["independent_runner"]["conclusion"]=="success",obj
assert v5e["verified"]["partial_batch_cannot_consume_epoch"] is True
assert v5e["verified"]["transient_failure_remains_unconsumed_and_retryable"] is True
assert v5e["verified"]["epoch_consumption_does_not_authorize_nonexistence"] is True
assert v5g["verified"]["v5_success_only_epoch_consumption_mandatory"] is True
assert candidate["mandatory_tool_discovery_retrieval"]["v5_live_gate_verification_git_blob_sha"]==FILES["v5g"][1]

# Hypergraph has exactly one Tool Discovery target action and it is retrieval-bound.
target="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
actions=[a for a in hyper["actions"] if target in (a.get("target_predicates") or [])]
assert len(actions)==1,len(actions)
action=actions[0]
assert action["id"]=="BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
assert isinstance(action.get("mandatory_retrieval_authority"),dict)
assert action["new_reality_units"]==0

# The current gate actually knows and enforces V5, not merely V3/V4.
for needle in (
 "V5_EXPECTED",
 "V5_DOES_NOT_PRESERVE_EXACT_V4_BASE",
 "v5_success_only_epoch_consumption_mandatory",
 "PASS__LIVE_TOOL_DISCOVERY_EDGE_MECHANICALLY_BOUND_TO_VERIFIED_V2_V3_V4_V5_RETRIEVAL_AUTHORITY",
):
 assert needle in gate,needle

# The live scheduler mechanically requires a gate result when Tool Discovery is unresolved,
# and main obtains that result from the repository at point of use.
for needle in (
 "tool_retrieval_gate_required = tool_retrieval_gate.TARGET in unresolved_set",
 "TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_NOT_PASS",
 "tool_retrieval_gate.evaluate_repository(root)",
):
 assert needle in scheduler,needle

# Candidate pins the exact current bytes.
assert candidate["live_scheduler"]["runtime_git_blob_sha"]==FILES["scheduler"][1]
assert candidate["live_scheduler"]["action_hypergraph_git_blob_sha"]==FILES["hypergraph"][1]
assert candidate["live_scheduler"]["retrieval_gate_git_blob_sha"]==FILES["gate"][1]
assert candidate["mandatory_tool_discovery_retrieval"]["authority"]=="V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE"
assert candidate["mandatory_tool_discovery_retrieval"]["failed_or_rejected_cell_consumed"] is False
assert candidate["mandatory_tool_discovery_retrieval"]["partial_batch_consumes_epoch"] is False
assert candidate["mandatory_tool_discovery_retrieval"]["open_world_no_result_means_nonexistence"] is False

# No credit smuggling.
for k in ("acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"):
 assert candidate[k]==0,(k,candidate[k])
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
assert candidate["fresh_reality_authority"] is False

print("TERMINAL_SCHEDULING_V13_RETRIEVAL_V5_VERIFIED")
print(json.dumps({
 "candidate_blob":FILES["candidate"][1],
 "scheduler_blob":FILES["scheduler"][1],
 "gate_blob":FILES["gate"][1],
 "hypergraph_blob":FILES["hypergraph"][1],
 "v5_live_gate_receipt_blob":FILES["v5g"][1],
 "scheduler_point_of_use_gate":True,
 "retrieval_v5_mandatory":True,
 "v12_scheduling_state_preserved":True,
 "zero_credit":True
},sort_keys=True))
