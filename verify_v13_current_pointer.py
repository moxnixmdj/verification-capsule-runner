#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FILES={
 "pointer":("subjects/v13_current_pointer_candidate.json","9ae934eb9971d59bf205823317f44e97709fa618"),
 "active":("subjects/v13_pointer_active_authority.json","d6546a99a62c77b79ae0b169e822ca4f636eea72"),
 "v13v":("subjects/v13_pointer_independent_verification.json","407313a62efa87c5f0fced98e25732b973b78baf"),
}

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(k):
    path,expected=FILES[k]
    p=ROOT/path
    actual=blob(p)
    assert actual==expected,(k,actual,expected)
    return json.loads(p.read_text(encoding="utf-8"))

for k,(p,e) in FILES.items():
    assert blob(ROOT/p)==e,(k,blob(ROOT/p),e)

ptr=load("pointer")
active=load("active")
v13v=load("v13v")

assert ptr["schema"]=="PROJECT_BRAIN_TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V13_CANDIDATE_V1"
assert ptr["current_authority"]["git_blob_sha"]==FILES["active"][1]
assert ptr["independent_verification"]["git_blob_sha"]==FILES["v13v"][1]
assert ptr["independent_verification"]["conclusion"]=="success"
assert v13v["independent_runner"]["conclusion"]=="success"
assert active["independent_verification"]["conclusion"]=="success"

live=ptr["live_world"]
assert (live["registry_predicates"],live["proved_predicates"],live["unresolved_predicates"])==(38,11,27)
assert live["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert live["active_zero_reality_requirements"]==17
assert live["active_nondominated_certificates"]==14
assert live["primitive_zero_reality_work_units"]==31
assert live["matched_priority_child_facts"]==16
assert live["direct_reality_blocked_predicates"]==[
 "FINANCE_UNCOVERED_SCOPE_AUDIT",
 "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
]

r=ptr["mandatory_tool_discovery_retrieval"]
assert r["authority"]=="V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
assert r["gate_git_blob_sha"]=="c3324e574c1fafb6aaab443f49b7a9600966e754"
assert r["strict_success_only_source_cell_consumption_required"] is True
assert r["transient_failures_retryable_and_unconsumed"] is True
assert r["partial_batch_epoch_consumption_allowed"] is False
assert r["all_selected_cells_required_before_epoch_consumption"] is True
assert r["off_domain_result_may_satisfy_source_cell"] is False
assert r["consumed_cell_replay_allowed"] is False
assert r["empty_or_failed_attempt_proves_nonexistence"] is False

for k in ("new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"):
    assert ptr[k]==0,(k,ptr[k])
assert ptr["execution_authority"] is False
assert ptr["promotion_authority"] is False
assert ptr["fresh_reality_authority"] is False

print("V13_CURRENT_POINTER_VERIFIED")
print(json.dumps({
 "pointer_blob":FILES["pointer"][1],
 "active_authority_blob":FILES["active"][1],
 "v13_verification_blob":FILES["v13v"][1],
 "live_world":"38/11/27__4_OF_19",
 "zero_reality_requirements":17,
 "primitive_work_units":31,
 "retrieval":"V5_OVER_V4_OVER_V3_OVER_V2",
 "zero_credit":True,
 "fresh_reality_authority":False
},sort_keys=True))
