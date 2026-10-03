#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import root1_acquisition_closure_controller_v2 as r1

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2.json").read_text())
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
assert root["roots"]["root_1_capability_missing"]["current_positive_root1_blockers"]==[]
assert root["scheduler_policy"]["root1_currently_active"] is False
assert gov["current_root1_truth"]["root1_positive_gap_count"]==0
assert gov["current_envelope_claim"]["frozen_envelope_sealed"] is False
assert gov["acceptance_credit_delta"]==0
assert gov["promotion_authority"] is False

tx=r1.acquisition_transaction(
    gap_evidence=None,
    required_primitives={"x"},
    verified_primitives=set(),
    actions=[{"id":"tempt","safe":True,"source_class":"code","p_close":1,"closure_mass":999,"time":1,"risk":0,"incremental_spend_usd":0}],
)
assert tx["status"]=="NO_ACTION_ROOT1_INACTIVE",tx
assert tx["selected_actions"]==[],tx

required={"a","b"}
receipt={
    "independent_verified":True,
    "exact_byte_bound":True,
    "conclusion":"success",
    "capability_set_complete":True,
    "envelope_id":"e",
    "primitive_set_sha256":r1._digest(required),
}
def route(pid,rid,status="VERIFIED_OWNED"):
    x={
      "primitive_id":pid,"route_id":rid,"route_status":status,
      "independent_verified":True,"exact_byte_bound":True,"content_addressed":True,
      "target_brain_owned_configuration":True,
      "future_use_requires_capability_rediscovery":False,
      "incremental_spend_usd":0,
    }
    if status=="VERIFIED_ACQUISITION_ROUTE":
      x.update({"internalizable":True,"executable":True,"source_admission_verified":True})
    return x

sealed=r1.compile_frozen_envelope(
    envelope_id="e",required_primitives=required,
    coverage_records=[route("a","ra"),route("b","rb","VERIFIED_ACQUISITION_ROUTE")],
    envelope_receipt=receipt,
)
assert sealed["root1_sealed_for_frozen_envelope"] is True,sealed
assert sealed["universal_semantic_learning_success_claimed"] is False

paid=route("b","paid","VERIFIED_ACQUISITION_ROUTE")
paid["incremental_spend_usd"]=1
open_result=r1.compile_frozen_envelope(
    envelope_id="e",required_primitives=required,
    coverage_records=[route("a","ra2"),paid],
    envelope_receipt=receipt,
)
assert open_result["root1_sealed_for_frozen_envelope"] is False,open_result
assert open_result["uncovered_primitives"]==["b"],open_result

try:
    r1.compile_frozen_envelope(
      envelope_id="e",required_primitives={"a"},coverage_records=[route("a","x")],
      envelope_receipt={"independent_verified":True},
    )
except r1.Root1ClosureError:
    pass
else:
    raise AssertionError("INCOMPLETE_ENVELOPE_RECEIPT_ACCEPTED")

stop=r1.search_stop_decision(
    selected_route_id="r",
    required_source_classes={"brain","code","official","papers","social"},
    searched_source_classes={"brain","code"},
)
assert stop["decision_complete"] is False,stop
inv={
  "independent_verified":True,
  "exact_byte_bound":True,
  "conclusion":"success",
  "all_remaining_sources_action_invariant":True,
  "selected_route_id":"r",
  "remaining_source_classes_sha256":r1._digest(stop["remaining_source_classes"]),
}
stop2=r1.search_stop_decision(
    selected_route_id="r",
    required_source_classes={"brain","code","official","papers","social"},
    searched_source_classes={"brain","code"},
    invariance_receipt=inv,
)
assert stop2["decision_complete"] is True,stop2
bad=dict(inv);bad["selected_route_id"]="other"
assert r1.search_stop_decision(
    selected_route_id="r",
    required_source_classes={"brain","code","official","papers","social"},
    searched_source_classes={"brain","code"},
    invariance_receipt=bad,
)["decision_complete"] is False

portfolio=r1.select_orthogonal_portfolio([
  {"id":"same1","safe":True,"source_class":"code","dependency_cluster":"g","p_close":1,"closure_mass":4,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"same2","safe":True,"source_class":"paper","dependency_cluster":"g","p_close":1,"closure_mass":3,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"orth","safe":True,"source_class":"official","dependency_cluster":"h","p_close":"1/2","closure_mass":4,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"paid","safe":True,"source_class":"social","dependency_cluster":"p","p_close":1,"closure_mass":999,"time":1,"risk":0,"incremental_spend_usd":1},
],max_actions=4)
assert "paid" not in [x["id"] for x in portfolio],portfolio
assert len({x["dependency_cluster"] for x in portfolio})==len(portfolio),portfolio
assert len({x["source_class"] for x in portfolio})==len(portfolio),portfolio

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V2_PUBLIC_RUNNER_RESULT",
  "status":"PASS__EXACT_BLOBS__DORMANT_GATE__FINITE_ENVELOPE__ZERO_SPEND_ACQUISITION__DECISION_COMPLETE_SEARCH_STOP__ORTHOGONAL_PORTFOLIO__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "root1_currently_inactive":True,
    "unknown_is_not_missing":True,
    "inactive_means_zero_action":True,
    "finite_envelope_seals_only_with_complete_exact_receipt":True,
    "verified_acquisition_route_requires_internalizable_executable_zero_cost_route":True,
    "paid_route_cannot_seal_envelope":True,
    "search_consensus_alone_cannot_stop":True,
    "residual_action_invariance_can_stop_search_when_exactly_bound":True,
    "source_and_dependency_orthogonalization":True,
    "zero_terminal_credit":True
  },
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False
},indent=2,sort_keys=True))
