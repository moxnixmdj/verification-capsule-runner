#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import decision_discriminator_v3 as decision
from canonical.runtime import meta_learning_policy_v2 as meta
from canonical.runtime import universal_learning_decision_router_v3 as router

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/UNIVERSAL_LEARNING_DECISION_ROUTER_V3.json").read_text())
assert gov["acceptance_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["capability_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["fresh_reality_authority"] is False
assert gov["unknown_domain_interpretation"]["acceptance_proved"] is False

def map_receipt(src,tgt,relation="EXACT",basis="CAUSAL_ISOMORPHISM",rid="map"):
    return {
        "receipt_id":rid,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "source_primitive":src,
        "target_primitive":tgt,
        "relation":relation,
        "mapping_basis":basis,
    }

mapping={
    "source_primitive":"A:law",
    "target_primitive":"B:latent-law",
    "relation":"EXACT",
    "mapping_basis":"CAUSAL_ISOMORPHISM",
    "verification_receipt":map_receipt("A:law","B:latent-law"),
    "provenance_chain":["source:verified","mapping:verified"],
}
out=router.route(
    goal="cross-domain",
    verified_coverage=True,
    required_facts={"B:latent-law"},
    verified_facts={"A:law"},
    transfer_mappings=[mapping],
    hypotheses=[],
    actions=[],
)
assert out["route"]=="USE_VERIFIED_CAPABILITY",out

bad=dict(mapping)
bad["verification_receipt"]=map_receipt("A:unrelated","B:unrelated")
try:
    transfer.admit(bad)
except transfer.StructuralTransferError:
    pass
else:
    raise AssertionError("UNRELATED_RECEIPT_ACCEPTED")

label=dict(mapping)
label["mapping_basis"]="LABEL_MATCH"
label["verification_receipt"]=map_receipt("A:law","B:latent-law",basis="LABEL_MATCH")
try:
    transfer.admit(label)
except transfer.StructuralTransferError:
    pass
else:
    raise AssertionError("LABEL_ONLY_TRANSFER_ACCEPTED")

hs=[
    {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
    {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
]
ranked=decision.rank(hypotheses=hs,actions=[
    {"id":"fake","safe":True,"outcome_by_hypothesis":{"h1":"same","h2":"same"},"decision_gain":999,"transfer_gain":999,"time":1},
    {"id":"real","safe":True,"outcome_by_hypothesis":{"h1":"left","h2":"right"},"decision_gain":0,"time":1},
])
assert [x["id"] for x in ranked]==["real"],ranked
assert ranked[0]["conditional_decision_gain"]=="1/2",ranked
assert "CONDITIONAL_ON_DECLARED" in ranked[0]["gain_basis"]

try:
    decision.rank(
        hypotheses=hs,
        actions=[{"id":"p","safe":True,"outcome_by_hypothesis":{"h1":"l","h2":"r"},"time":1}],
        transfer_weight="-1",
    )
except decision.DecisionDiscriminatorError:
    pass
else:
    raise AssertionError("NEGATIVE_WEIGHT_ACCEPTED")

consensus=router.route(
    goal="decision sufficient",
    verified_coverage=False,
    required_facts={"unknown"},
    verified_facts=set(),
    transfer_mappings=[],
    hypotheses=[
        {"id":"h1","plausible":True,"best_action":"STOP","probability":"1/2"},
        {"id":"h2","plausible":True,"best_action":"STOP","probability":"1/2"},
    ],
    actions=[{"id":"expensive","safe":True,"outcome_by_hypothesis":{"h1":"l","h2":"r"},"time":100}],
)
assert consensus["route"]=="DECISION_SUFFICIENT_UNVERIFIED_MODEL",consensus
assert consensus["trusted_execution_authorized"] is False
assert consensus["promotion_authorized"] is False

abstain=router.route(
    goal="ambiguous",
    verified_coverage=False,
    required_facts={"unknown"},
    verified_facts=set(),
    transfer_mappings=[],
    hypotheses=hs,
    actions=[{"id":"useless","safe":True,"outcome_by_hypothesis":{"h1":"same","h2":"same"},"transfer_gain":1000,"proof_gain":1000,"time":1}],
)
assert abstain["route"]=="ABSTAIN_OR_REQUEST_DISCRIMINATOR",abstain

try:
    meta.compare(
        episodes=[
            {"task_id":"t","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":1,"reality_calls":1,"information_actions":1},
            {"task_id":"t","strategy_id":"new","verified":True,"success":True,"safety_violation":False,"wall_clock":-1,"reality_calls":0,"information_actions":0},
        ],
        incumbent="old",
        candidate="new",
    )
except meta.MetaLearningPolicyError:
    pass
else:
    raise AssertionError("NEGATIVE_META_COST_ACCEPTED")

comparison=meta.compare(
    episodes=[
        {"task_id":"t1","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":10,"reality_calls":2,"information_actions":5},
        {"task_id":"t2","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":10,"reality_calls":2,"information_actions":5},
        {"task_id":"t1","strategy_id":"new","verified":True,"success":True,"safety_violation":False,"wall_clock":5,"reality_calls":1,"information_actions":4},
        {"task_id":"t2","strategy_id":"new","verified":True,"success":True,"safety_violation":False,"wall_clock":6,"reality_calls":1,"information_actions":4},
    ],
    incumbent="old",
    candidate="new",
)
assert comparison["preference_admissible"] is True
receipt={
    "receipt_id":"meta-v",
    "independent_verified":True,
    "exact_byte_bound":True,
    "conclusion":"success",
    "environment_class":"unseen-api",
    "candidate_strategy":"new",
    "comparison_sha256":comparison["comparison_sha256"],
}
policy=meta.compile_policy(
    environment_class="unseen-api",
    comparison=comparison,
    candidate_strategy="new",
    verification_receipt=receipt,
)
assert policy["scope"]=="MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY"
assert policy["promotion_authorized"] is False

wrong=dict(receipt)
wrong["comparison_sha256"]="sha256:"+"0"*64
try:
    meta.compile_policy(
        environment_class="unseen-api",
        comparison=comparison,
        candidate_strategy="new",
        verification_receipt=wrong,
    )
except meta.MetaLearningPolicyError:
    pass
else:
    raise AssertionError("UNBOUND_META_RECEIPT_ACCEPTED")

print(json.dumps({
    "schema":"PROJECT_BRAIN_UNIVERSAL_LEARNING_DECISION_ROUTER_V3_PUBLIC_RUNNER_RESULT_V1",
    "status":"PASS__EXACT_BLOBS__STRUCTURAL_TRANSFER_BINDING__CONDITIONAL_DISCRIMINATION__EVIDENCE_BOUND_META_POLICY__ZERO_CREDIT",
    "pass":True,
    "verified":{
        "exact_brain_blob_identities":True,
        "structural_transfer_receipt_bound_to_exact_mapping":True,
        "surface_only_transfer_rejected":True,
        "caller_claimed_decision_gain_non_load_bearing":True,
        "conditional_probability_weighted_decision_gain":True,
        "negative_objective_weight_rejected":True,
        "decision_sufficiency_stops_extra_probe":True,
        "nondiscriminator_cannot_buy_way_out_of_abstention":True,
        "negative_meta_cost_rejected":True,
        "meta_policy_receipt_bound_to_exact_comparison":True,
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
