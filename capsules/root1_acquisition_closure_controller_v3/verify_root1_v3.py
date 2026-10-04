#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import root1_acquisition_closure_controller_v3 as r3

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3.json").read_text())
audit=json.loads((ROOT/"canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V1.json").read_text())

assert gov["scope"]=="ROOT1_CAPABILITY_MISSING_ONLY"
assert gov["current_root1_truth"]["root1_positive_gap_count"]==0
assert gov["current_root1_truth"]["root1_currently_active"] is False
assert gov["current_root1_truth"]["route_coverage_unproved_is_not_missing"] is True
assert gov["current_root1_truth"]["root1_frozen_envelope_sealed"] is False
assert gov["accounting"]["incremental_spend_usd"]==0
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False

assert audit["declared_terminal_family_envelope"]["expected_family_count"]==19
assert audit["declared_terminal_family_envelope"]["actual_family_count"]==19
assert audit["declared_terminal_family_envelope"]["complete_primitive_causal_basis_claimed"] is False
assert audit["verified_owned_count"]==5
assert audit["route_coverage_unproved_count"]==14
assert len(audit["verified_owned_families"])==5
assert len(audit["route_coverage_unproved_families"])==14
assert not (set(audit["verified_owned_families"]) & set(audit["route_coverage_unproved_families"]))
assert len(set(audit["verified_owned_families"]) | set(audit["route_coverage_unproved_families"]))==19
assert audit["classification"]["root1_positive_gap_count"]==0
assert audit["classification"]["route_coverage_unproved_is_capability_missing"] is False

# Bayesian estimator: no fabricated certainty; Jeffreys prior gives 1/2 before observations.
assert r3.beta_posterior_mean(0,0)==Fraction(1,2)
assert r3.beta_posterior_mean(10,10)==Fraction(21,22)
assert r3.beta_posterior_mean(0,10)==Fraction(1,22)
try:
    r3.beta_posterior_mean(11,10)
except r3.Root1V3Error:
    pass
else:
    raise AssertionError("IMPOSSIBLE_BETA_HISTORY_ACCEPTED")

# Ranking must eliminate paid routes and discount duplicated/correlated evidence.
ranked=r3.rank_probabilistic_actions([
  {"id":"orthogonal","safe":True,"source_class":"official","dependency_cluster":"o","historical_successes":2,"historical_attempts":4,"closure_mass":10,"time":1,"risk":0,"correlation_penalty":0,"incremental_spend_usd":0},
  {"id":"correlated","safe":True,"source_class":"code","dependency_cluster":"c","historical_successes":2,"historical_attempts":4,"closure_mass":10,"time":1,"risk":0,"correlation_penalty":9,"incremental_spend_usd":0},
  {"id":"paid","safe":True,"source_class":"social","dependency_cluster":"p","historical_successes":100,"historical_attempts":100,"closure_mass":1000,"time":1,"risk":0,"correlation_penalty":0,"incremental_spend_usd":"0.01"},
])
assert ranked[0]["id"]=="orthogonal",ranked
assert "paid" not in [x["id"] for x in ranked],ranked

portfolio=r3.select_probabilistic_orthogonal_portfolio([
  {"id":"a","safe":True,"source_class":"code","dependency_cluster":"same","historical_successes":1,"historical_attempts":1,"closure_mass":9,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"b","safe":True,"source_class":"paper","dependency_cluster":"same","historical_successes":1,"historical_attempts":1,"closure_mass":8,"time":1,"risk":0,"incremental_spend_usd":0},
  {"id":"c","safe":True,"source_class":"official","dependency_cluster":"other","historical_successes":1,"historical_attempts":1,"closure_mass":7,"time":1,"risk":0,"incremental_spend_usd":0},
],max_actions=3)
assert len({x["source_class"] for x in portfolio})==len(portfolio),portfolio
assert len({x["dependency_cluster"] for x in portfolio})==len(portfolio),portfolio

# Exact set cover must choose cheaper multi-route cover over a broad expensive route.
cover=r3.minimum_weight_route_cover(
  missing_primitives={"a","b","c","d"},
  routes=[
    {"id":"ab","safe":True,"covers":["a","b"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":0},
    {"id":"cd","safe":True,"covers":["c","d"],"time":1,"risk":0,"complexity":0,"incremental_spend_usd":0},
    {"id":"all","safe":True,"covers":["a","b","c","d"],"time":3,"risk":0,"complexity":0,"incremental_spend_usd":0},
    {"id":"paid_all","safe":True,"covers":["a","b","c","d"],"time":"1/100","risk":0,"complexity":0,"incremental_spend_usd":1},
  ],
)
assert cover["status"]=="EXACT_MINIMUM_ADMISSIBLE_ROUTE_COVER",cover
assert cover["selected_route_ids"]==["ab","cd"],cover
assert cover["total_weight"]=="2",cover

# Inactive Root1 must schedule exactly zero acquisition even if a perfect route is supplied.
tx=r3.root1_atomic_transaction(
  gap_evidence=None,
  required_primitives={"x"},
  verified_primitives=set(),
  search_actions=[{"id":"perfect","safe":True,"source_class":"code","historical_successes":100,"historical_attempts":100,"closure_mass":999,"time":1,"risk":0,"incremental_spend_usd":0}],
  acquisition_routes=[{"id":"instant","safe":True,"covers":["x"],"time":"1/1000","risk":0,"complexity":0,"incremental_spend_usd":0}],
)
assert tx["status"]=="ROOT1_INACTIVE_ZERO_ACQUISITION_ACTIONS",tx
assert tx["search_portfolio"]==[],tx
assert tx["route_cover"] is None,tx

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_PUBLIC_RUNNER_RESULT",
  "status":"PASS__EXACT_BLOBS__ROOT1_BOUNDARY__JEFFREYS_POSTERIOR__CORRELATION_PENALTY__ORTHOGONAL_PORTFOLIO__EXACT_ZERO_SPEND_ROUTE_COVER__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "root1_inactive_zero_action":True,
    "route_coverage_unproved_not_missing":True,
    "declared_19_family_partition_exact_5_plus_14":True,
    "jeffreys_prior_no_false_certainty":True,
    "paid_routes_rejected":True,
    "correlation_penalty_load_bearing":True,
    "source_dependency_orthogonalization":True,
    "exact_minimum_weight_route_cover":True,
    "root1_seal_remains_false":True,
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
