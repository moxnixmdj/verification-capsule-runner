#!/usr/bin/env python3
from __future__ import annotations

import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import universal_learning_active_router_v2 as router

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/UNIVERSAL_LEARNING_ACTIVE_ROUTER_V2.json").read_text())
v1=json.loads((ROOT/"canonical/verification/UNIVERSAL_LEARNING_CONTRACT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text())
v2=json.loads((ROOT/"canonical/verification/UNIVERSAL_ACTIVE_TRANSFER_LEARNER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json").read_text())
assert v1["independent_runner"]["conclusion"]=="success"
assert v2["independent_runner"]["conclusion"]=="success"

known=router.route(
    goal="reuse",
    verified_coverage=True,
    required_facts={"a","b"},
    verified_facts={"a","b"},
    hypotheses=[],
    actions=[],
)
assert known["route"]=="USE_VERIFIED_CAPABILITY",known
assert known["trusted_execution_authorized"] is True,known

contradicted=router.route(
    goal="changed environment",
    verified_coverage=True,
    required_facts={"a","b"},
    verified_facts={"a"},
    hypotheses=[{"id":"h1","plausible":True,"best_action":"inspect"}],
    actions=[{"id":"inspect","decision_gain":2,"transfer_gain":1,"proof_gain":1,"time":1,"cost":0,"risk":0}],
)
assert contradicted["route"]=="LEARN",contradicted
assert contradicted["reason"]=="VERIFIED_COVERAGE_CONTRADICTED_BY_NOVELTY_DELTA",contradicted
assert contradicted["trusted_execution_authorized"] is False,contradicted

# V2 fact coverage may never override V1's explicit verification gate.
v1_false_even_if_facts_covered=router.route(
    goal="coverage is not authority",
    verified_coverage=False,
    required_facts={"a"},
    verified_facts={"a"},
    hypotheses=[],
    actions=[],
)
assert v1_false_even_if_facts_covered["route"]=="ABSTAIN_OR_REQUEST_DISCRIMINATOR",v1_false_even_if_facts_covered
assert v1_false_even_if_facts_covered["trusted_execution_authorized"] is False,v1_false_even_if_facts_covered

learn=router.route(
    goal="new environment",
    verified_coverage=False,
    required_facts={"mechanism"},
    verified_facts=set(),
    hypotheses=[
      {"id":"h1","plausible":True,"best_action":"probe"},
      {"id":"h2","plausible":True,"best_action":"inspect"},
    ],
    actions=[
      {"id":"search","decision_gain":2,"transfer_gain":0,"proof_gain":0,"time":4,"cost":0,"risk":0},
      {"id":"probe","decision_gain":2,"transfer_gain":2,"proof_gain":2,"time":1,"cost":0,"risk":0},
    ],
)
assert learn["route"]=="LEARN",learn
assert learn["next_action"]["id"]=="probe",learn

abstain=router.route(
    goal="safe choice",
    verified_coverage=False,
    required_facts={"hidden"},
    verified_facts=set(),
    hypotheses=[
      {"id":"h1","plausible":True,"best_action":"left"},
      {"id":"h2","plausible":True,"best_action":"right"},
    ],
    actions=[],
)
assert abstain["route"]=="ABSTAIN_OR_REQUEST_DISCRIMINATOR",abstain
assert abstain["trusted_execution_authorized"] is False,abstain

consensus=router.route(
    goal="decision sufficient",
    verified_coverage=False,
    required_facts={"hidden"},
    verified_facts=set(),
    hypotheses=[
      {"id":"h1","plausible":True,"best_action":"stop"},
      {"id":"h2","plausible":True,"best_action":"stop"},
    ],
    actions=[],
)
assert consensus["route"]=="DECISION_SUFFICIENT_UNVERIFIED_MODEL",consensus
assert consensus["recommended_action"]=="stop",consensus
assert consensus["trusted_execution_authorized"] is False,consensus
assert consensus["promotion_authorized"] is False,consensus

for out in (known,contradicted,v1_false_even_if_facts_covered,learn,abstain,consensus):
    assert out["acceptance_credit_delta"]==0,out
    assert out["family_credit_delta"]==0,out
    assert out["capability_credit_delta"]==0,out
    assert out["ownership_credit_delta"]==0,out

assert gov["trusted_route_rule"]=="V1_USE_VERIFIED_CAPABILITY_AND_NOVELTY_DELTA_EMPTY"
assert gov["unknown_domain_bridge"]["status"]=="STRUCTURAL_PARTIAL_ONLY"
assert gov["unknown_domain_bridge"]["unknown_domain_acceptance_proved"] is False
assert gov["acceptance_credit_delta"]==0
assert gov["ownership_credit_delta"]==0

print(json.dumps({
  "schema":"PROJECT_BRAIN_UNIVERSAL_LEARNING_ACTIVE_ROUTER_V2_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__V1_SAFETY_DOMINATES_V2_OPTIMIZATION__CALIBRATED_FAIL_CLOSED_ROUTING_VERIFIED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_brain_blob_identities":True,
    "v1_verified_route_requires_zero_novelty_delta":True,
    "novelty_contradicts_stale_verified_coverage":True,
    "v2_fact_coverage_cannot_override_v1_authority":True,
    "optimized_learning_route":True,
    "decision_sufficient_unverified_model_route":True,
    "abstain_or_request_discriminator_route":True,
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
