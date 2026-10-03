#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import root1_capability_acquisition_controller_v1 as r1

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/ROOT1_CAPABILITY_ACQUISITION_CONTROLLER_V1.json").read_text())
assert gov["current_root1_truth"]["root1_positive_gap_count"]==0
assert gov["current_root1_truth"]["default_action"]=="NO_ACTION"
assert gov["incremental_spend_usd"]==0
assert gov["acceptance_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["capability_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["fresh_reality_authority"] is False
assert gov["promotion_authority"] is False

u=r1.classify_root1({"positive_operational_gap":True,"required_behavior":"mystery"})
assert u["root1_active"] is False,u
assert u["reason"]=="UNKNOWN_OR_UNPROVED_IS_NOT_MISSING",u

e={
  "positive_operational_gap":True,
  "required_behavior":"restore",
  "constructive_witness_verified":True,
  "constructive_witness_content_addressed":True,
  "operative_failure_demonstrated":True,
  "acquisition_routes_accounted":True,
  "unresolved_after_available_acquisition":True,
}
g=r1.classify_root1(e)
assert g["root1_active"] is True,g

mapping={
  "source_primitive":"old:p",
  "target_primitive":"new:q",
  "relation":"EXACT",
  "mapping_basis":"CAUSAL_ISOMORPHISM",
  "verification_receipt":{
    "receipt_id":"map",
    "independent_verified":True,
    "exact_byte_bound":True,
    "conclusion":"success",
    "source_primitive":"old:p",
    "target_primitive":"new:q",
    "relation":"EXACT",
    "mapping_basis":"CAUSAL_ISOMORPHISM",
  },
  "provenance_chain":["source","map"],
}
d=r1.minimum_capability_delta(
    required_primitives={"new:q","new:r"},
    verified_primitives={"old:p"},
    transfer_mappings=[mapping],
)
assert d["missing_primitives"]==["new:r"],d

ranked=r1.rank_acquisition_actions([
  {"id":"free","safe":True,"source_class":"code","p_close":"1/2","terminal_leverage":2,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"paid","safe":True,"source_class":"paper","p_close":1,"terminal_leverage":100,"information_gain":100,"time":1,"risk":0,"incremental_spend_usd":1},
])
assert [x["id"] for x in ranked]==["free"],ranked

ranked=r1.rank_acquisition_actions([
  {"id":"dup","safe":True,"source_class":"web","p_close":"1/2","terminal_leverage":2,"information_gain":1,"time":1,"risk":0,"correlation_with_selected":1,"incremental_spend_usd":0},
  {"id":"orth","safe":True,"source_class":"code","p_close":"1/2","terminal_leverage":2,"information_gain":1,"time":1,"risk":0,"correlation_with_selected":0,"incremental_spend_usd":0},
])
assert ranked[0]["id"]=="orth",ranked

portfolio=r1.select_orthogonal_portfolio([
  {"id":"w1","safe":True,"source_class":"web","p_close":"3/4","terminal_leverage":4,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"w2","safe":True,"source_class":"web","p_close":"2/3","terminal_leverage":4,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"c1","safe":True,"source_class":"code","p_close":"1/2","terminal_leverage":4,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
],max_actions=3,max_same_source_class=1)
assert {x["source_class"] for x in portfolio}=={"web","code"},portfolio

exp=r1.choose_experiment([
  {"id":"slow","safe":True,"expected_information_gain":4,"time":4,"risk":0,"incremental_spend_usd":0},
  {"id":"fast","safe":True,"expected_information_gain":3,"time":1,"risk":0,"incremental_spend_usd":0},
])
assert exp["id"]=="fast",exp

try:
    r1.structural_abstraction(
      concrete_mechanism="x",
      abstract_pattern="y",
      verification_receipts=[{"receipt_id":"bad","independent_verified":False,"exact_byte_bound":True,"conclusion":"success"}],
    )
except r1.Root1ControllerError:
    pass
else:
    raise AssertionError("UNVERIFIED_ABSTRACTION_RECEIPT_ACCEPTED")

tx=r1.acquisition_transaction(
    gap_evidence=None,
    required_primitives={"x"},
    verified_primitives=set(),
    actions=[{"id":"tempting","safe":True,"source_class":"web","p_close":1,"terminal_leverage":999,"information_gain":999,"time":1,"risk":0,"incremental_spend_usd":0}],
)
assert tx["status"]=="NO_ACTION_ROOT1_INACTIVE",tx
assert tx["selected_actions"]==[],tx
assert tx["selected_experiment"] is None,tx
assert tx["fresh_reality_authority"] is False
assert tx["promotion_authority"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT1_CAPABILITY_ACQUISITION_CONTROLLER_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_BLOBS__DORMANT_GATE__MINIMUM_DELTA__ZERO_SPEND__ORTHOGONAL_ACQUISITION__EXPERIMENT_FALLBACK__PROOF_PRESERVING_ABSTRACTION__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "unknown_is_not_missing":True,
    "constructive_gap_gate":True,
    "receipt_bound_structural_transfer":True,
    "hard_zero_spend_filter":True,
    "correlation_penalty":True,
    "orthogonal_source_portfolio":True,
    "safe_information_gain_experiment_fallback":True,
    "proof_preserving_abstraction_gate":True,
    "root1_inactive_zero_action":True,
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
