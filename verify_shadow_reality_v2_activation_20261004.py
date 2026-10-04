#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
S=ROOT/"subject"/"shadow_reality_v2_activation_20261004"
A=S/"PROOF_CARRYING_SHADOW_REALITY_V2_ACTIVATION_V1.json"
R=S/"TERMINAL_ROOT_CAUSE_STATE_V1.json"

EXPECTED_A="df8bce24360102395f397b28399e0e8e5fb9f6d4"
EXPECTED_R="36ac53134b123cfed7e63c31a871a30f9b4579e4"

def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

assert blob(A)==EXPECTED_A
assert blob(R)==EXPECTED_R

a=json.loads(A.read_text())
r=json.loads(R.read_text())

cur=r["current_acceptance"]
assert a["bound_main_commit"]=="50697f29b56afbf72654ccc9aef548bcb5368ffa"
assert a["implementation"]["runtime_git_blob_sha"]=="fd5639e9d503f59913bfbd08e47799ef5132b1e7"
assert a["implementation"]["policy_git_blob_sha"]=="756a608f0a3acaa72e56abbaa078f1cf0f3df938"
assert a["implementation"]["independent_verifier_commit"]=="96e72332a433d576f40bddb0a620cf45e0c49441"
assert a["implementation"]["independent_verifier_conclusion"]=="success"

p=a["terminal_state_preserved"]
assert p["accepted_families"]==cur["accepted_families"]==5
assert p["open_families"]==cur["open_families"]==14
assert p["proved_atomic"]==cur["proved_atomic"]==12
assert p["unresolved_atomic"]==cur["unresolved_atomic"]==26
assert p["terminal"] is cur["terminal"] is False

root1=r["roots"]["root_1_capability_missing"]["current_blocker_classification_seal"]["current_main_live_recomputation"]
assert p["root1_positive_gap_count"]==root1["root1_positive_gaps"]==0

auth=a["authority_semantics"]
assert auth["scheduling_authority"] is True
assert auth["per_route_shadow_collection_authority"] is True
for k in (
    "result_release_authority",
    "terminal_execution_authority",
    "acceptance_credit_authority",
    "promotion_authority",
    "global_fresh_reality_promotion_authority",
):
    assert auth[k] is False

acct=a["accounting"]
for k in (
    "incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed",
    "acceptance_credit_delta","family_credit_delta","capability_credit_delta",
    "ownership_credit_delta"
):
    assert acct[k]==0

rules="\n".join(a["hard_rules"])
assert "NO_RESULT_MAY_AFFECT_CANDIDATE_SELECTION_MUTATION_SCHEDULING_OR_ACCEPTANCE_BEFORE_RELEASE" in rules
assert "GLOBAL_FRESH_REALITY_PROMOTION_AUTHORITY_REMAINS_FALSE" in rules
assert "NO_REPLAY_OR_SECOND_EXECUTION_UNDER_ONE_USE_LEASE" in rules

gates=set(a["per_route_activation_gate"])
required={
 "VERIFY_SHADOW_REALITY_LEASE_RETURNS_SHADOW_COLLECTION_READY_TRUE",
 "UNDERLYING_GENERIC_ISOLATION_RECEIPT_REVERIFIED",
 "UNDERLYING_BENCHMARK_THIN_ADAPTER_REVERIFIED",
 "ZERO_INCREMENTAL_SPEND_GUARD_TRUE",
 "RESULT_ESCROWED_AND_HIDDEN_FROM_CANDIDATE_OPTIMIZER_AND_MUTATORS",
 "RELEASE_REQUIRES_ZERO_REALITY_FIXED_POINT",
 "RELEASE_REQUIRES_INDEPENDENT_VERIFICATION",
}
assert required <= gates

# Candidate must still be inactive before this verifier is bound.
assert a["active"] is False

print("PASS: shadow reality V2 activation preserves current root truth and grants collection-only authority")
