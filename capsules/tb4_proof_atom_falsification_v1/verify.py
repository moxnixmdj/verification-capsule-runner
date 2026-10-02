from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
    "attainability_cut.json":"ea5b05a30b02ba29a57fc931ea30137c588493d2",
    "attainability_verdict.json":"a7b0c692251b92819007c581b9fe84b75960cab7",
    "evidence_manifest.json":"36cfd7b29465a2da6c05667b18848bdcabcd22e6",
}
PROPOSITION="MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"
TARGET="CODING_TB4_GE_66_4"

def blob_sha(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name: str):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

for name,expected in EXPECTED.items():
    got=blob_sha(ROOT/name)
    assert got==expected,(name,got,expected)

cut=load("attainability_cut.json")
verdict=load("attainability_verdict.json")
manifest=load("evidence_manifest.json")

assert cut["status"].startswith("ACTIVE_FAIL_CLOSED__INDEPENDENT_PUBLIC_RUNNER_PASS"), cut["status"]
assert verdict["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__ROUTE_IMPOSSIBLE__ZERO_CASES", verdict["status"]
assert verdict["independent_verification"]["conclusion"]=="success"
assert verdict["independent_verification"]["exact_attainability_replay"] is True
assert verdict["fresh_acceptance_cases_consumed"]==0

triples=[
    (cut["current_tb4"]["upper_bound_successes"],cut["current_tb4"]["required_successes"]),
    (verdict["result"]["upper_bound_successes"],verdict["result"]["required_successes"]),
    (manifest["derived"]["maximum_attainable_successes"],manifest["derived"]["required_successes"]),
]
assert triples==[(180,220),(180,220),(180,220)],triples
assert all(upper < required for upper,required in triples)
assert cut["current_tb4"]["attainability_state"]=="IMPOSSIBLE"
assert verdict["result"]["attainability_state"]=="IMPOSSIBLE"
assert cut["current_tb4"]["reality_execution_authorized"] is False
assert verdict["result"]["reality_execution_authorized"] is False
assert verdict["result"]["inequality"]=="180_LT_220"
assert manifest["derived"]["inequality"]=="180_LT_220"

# The active atom asserts a machine-verified upper bound >=220 for this frozen route.
# Exact independently replayed sources instead bind the upper bound to 180.
atom_truth=(verdict["result"]["upper_bound_successes"] >= 220)
assert atom_truth is False

out={
  "schema":"PROJECT_BRAIN_PROOF_ATOM_ZERO_REALITY_ADJUDICATION_V1",
  "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TB4_CURRENT_ROUTE_ATOM_FALSIFIED__ZERO_NEW_REALITY__ZERO_CREDIT",
  "atom":{"proposition":PROPOSITION,"target_predicate":TARGET,"truth_under_bound_route":False},
  "proof":{
    "upper_bound_successes":180,
    "required_successes":220,
    "inequality":"180_LT_220",
    "fresh_acceptance_cases_consumed":0,
    "source_git_blob_shas":EXPECTED,
  },
  "scope":"CURRENT_FROZEN_TB4_NO_REPLAY_ROUTE_ONLY__TARGET_PREDICATE_REMAINS_OPEN__ALTERNATIVE_TARGET_PRESERVING_CERTIFICATE_MAY_REOPEN",
  "capability_credit_delta":0,
  "family_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False,
}
print(json.dumps(out,indent=2,sort_keys=True))
