#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_atomic_claim_control_v1_sol"
RUNTIME=SUB/"shadow_atomic_one_use_claim_control_v1.py"
TEST=SUB/"test_shadow_atomic_one_use_claim_control_v1.py"
GOV=SUB/"SHADOW_ATOMIC_ONE_USE_CLAIM_CONTROL_V1.json"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(RUNTIME)=="d371e6b7f67e22de3bc0518d7e0400d8f54cab14"
assert blob(TEST)=="4b6a5aeefa3a419c4857a8c9e0e148576717bc98"
assert blob(GOV)=="913c908bf97cecf520789e868a3781f4b0472c38"

spec=importlib.util.spec_from_file_location("claim",RUNTIME)
assert spec and spec.loader
claim=importlib.util.module_from_spec(spec)
sys.modules["claim"]=claim
spec.loader.exec_module(claim)

d="a"*64
good={
 "lease_digest_sha256":d,
 "claim_ref":claim.expected_claim_ref(d),
 "atomic_create_attempted":True,
 "atomic_create_succeeded":True,
 "create_http_status":201,
 "reference_already_exists":False,
 "case_reveal_before_claim":False,
 "execution_started_before_claim":False,
 "claim_response_bound_to_exact_ref":True,
 "claim_response_bound_to_exact_lease":True,
}
out=claim.verify_atomic_claim_event(good)
assert out["atomic_one_use_claim_pass"] is True
assert out["prior_absence_observation_required"] is False
assert out["case_reveal_authority"] is False
assert out["shadow_collection_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False

# Absence observation is neither required nor sufficient.
with_absence=dict(good); with_absence["claim_ref_absent_observed"]=True
assert claim.verify_atomic_claim_event(with_absence)["atomic_one_use_claim_pass"] is True
bad=dict(with_absence)
bad.update({"atomic_create_succeeded":False,"create_http_status":422,"reference_already_exists":True,"create_error":"Reference already exists"})
badout=claim.verify_atomic_claim_event(bad)
assert badout["atomic_one_use_claim_pass"] is False
assert claim.classify_failed_create(bad)=="REPLAY_OR_DUPLICATE_REJECTED"

mutations=[
 ("wrong_ref",{"claim_ref":"refs/heads/shadow-claims/wrong"},"CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST"),
 ("no_attempt",{"atomic_create_attempted":False},"ATOMIC_CREATE_NOT_ATTEMPTED"),
 ("early_reveal",{"case_reveal_before_claim":True},"CASE_REVEAL_OCCURRED_BEFORE_CLAIM"),
 ("early_exec",{"execution_started_before_claim":True},"EXECUTION_STARTED_BEFORE_CLAIM"),
 ("unbound_ref",{"claim_response_bound_to_exact_ref":False},"CLAIM_RESPONSE_NOT_BOUND_TO_EXACT_REF"),
 ("unbound_lease",{"claim_response_bound_to_exact_lease":False},"CLAIM_RESPONSE_NOT_BOUND_TO_EXACT_LEASE"),
]
for name,delta,reason in mutations:
    r=dict(good); r.update(delta)
    o=claim.verify_atomic_claim_event(r)
    assert o["atomic_one_use_claim_pass"] is False,(name,o)
    assert reason in o["reasons"],(name,o)

gov=json.loads(GOV.read_text())
assert gov["semantics"]["prior_absence_observation_required"] is False
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert gov["accounting"]["terminal_cases_consumed"]==0

print(json.dumps({
 "status":"PASS",
 "runtime_git_blob_sha":blob(RUNTIME),
 "test_git_blob_sha":blob(TEST),
 "governance_git_blob_sha":blob(GOV),
 "negative_mutation_count":len(mutations)+1,
 "prior_absence_observation_required":False,
 "terminal_cases_consumed":0,
 "case_reveal_authority":False,
 "shadow_collection_authority":False,
 "fresh_reality_authority":False,
},sort_keys=True))
