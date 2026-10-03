#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import universal_active_transfer_learner_v2 as v2

def blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/UNIVERSAL_ACTIVE_TRANSFER_LEARNER_V2.json").read_text(encoding="utf-8"))
v1_receipt=json.loads((ROOT/"canonical/verification/UNIVERSAL_LEARNING_CONTRACT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text(encoding="utf-8"))

assert v1_receipt["independent_runner"]["conclusion"]=="success"
assert v1_receipt["verified"]["unknown_capture_total"] is True
assert v1_receipt["verified"]["candidate_requires_verification_before_trust"] is True
assert v1_receipt["verified"]["promotion_requires_verified_state"] is True

# Novelty compression.
d=v2.minimum_novelty_delta(
    required_facts={"syntax","types","ownership","borrow-checker"},
    verified_facts={"syntax","types","ownership"},
)
assert d["missing"]==["borrow-checker"],d
assert d["covered"]==["ownership","syntax","types"],d
assert abs(d["novelty_ratio"]-0.25)<1e-12,d
assert d["acceptance_credit"] is False
assert d["ownership_credit"] is False

# Decision-relevant value density.
r=v2.rank_learning_actions([
    {"id":"search","decision_gain":5,"transfer_gain":1,"proof_gain":1,"time":5,"cost":0,"risk":0},
    {"id":"probe","decision_gain":4,"transfer_gain":2,"proof_gain":2,"time":1,"cost":0,"risk":0},
])
assert r[0]["id"]=="probe",r

# Adversarial invalid action dimensions fail closed.
for bad in (
    {"id":"bad-time","decision_gain":1,"time":-1,"cost":0,"risk":0},
    {"id":"zero-cost-all","decision_gain":1,"time":0,"cost":0,"risk":0},
):
    try:
        v2.rank_learning_actions([bad])
    except v2.ActiveTransferLearnerError:
        pass
    else:
        raise AssertionError(("BAD_ACTION_ACCEPTED",bad))

# Hypotheses are not eliminated by mere inconvenience.
h=v2.update_hypotheses([
    {"id":"h1","plausible":True,"best_action":"inspect"},
    {"id":"h2","plausible":True,"best_action":"probe"},
    {"id":"h3","plausible":False,"best_action":"stop"},
],contradicted_ids={"h2"})
assert h["live_ids"]==["h1"],h
assert h["eliminated_ids"]==["h2","h3"],h

# Stop only when all live hypotheses agree.
assert v2.decision_sufficient([
    {"id":"h1","plausible":True,"best_action":"A"},
    {"id":"h2","plausible":True,"best_action":"A"},
])["sufficient"] is True
assert v2.decision_sufficient([
    {"id":"h1","plausible":True,"best_action":"A"},
    {"id":"h2","plausible":True,"best_action":"B"},
])["sufficient"] is False

# Change invalidates only the dependency cone.
cone=v2.invalidation_cone(
    changed={"api-v2"},
    dependencies={
        "api-v2":["auth-route","upload-skill"],
        "auth-route":["login-workflow"],
        "upload-skill":[],
        "login-workflow":[],
        "unrelated":[],
    },
)
assert cone["invalidated"]==["api-v2","auth-route","login-workflow","upload-skill"],cone
assert cone["preserved"]==["unrelated"],cone

# Skill compilation requires proof and grants zero terminal credit.
skill=v2.compile_verified_skill(
    skill_id="schema-first",
    applicability={"unfamiliar-api"},
    dependencies={"schema-visible"},
    invalidators={"schema-changed"},
    verification_receipts={"receipt-1"},
)
assert skill["trusted"] is True
assert skill["promotion_authorized"] is False
assert skill["acceptance_credit"] is False
assert skill["ownership_credit"] is False
try:
    v2.compile_verified_skill(
        skill_id="unsafe",
        applicability={"x"},
        dependencies=set(),
        invalidators=set(),
        verification_receipts=set(),
    )
except v2.ActiveTransferLearnerError:
    pass
else:
    raise AssertionError("UNVERIFIED_SKILL_COMPILED")

# Meta-learning requires a verified episode.
meta=v2.compile_learning_strategy({
    "domain":"unfamiliar-api",
    "verified":True,
    "actions":[
        {"kind":"search","decision_gain":1,"time":5},
        {"kind":"schema-inspection","decision_gain":5,"time":1},
    ],
})
assert meta["preferred_action_kind"]=="schema-inspection",meta
assert meta["acceptance_credit"] is False
assert meta["ownership_credit"] is False
try:
    v2.compile_learning_strategy({
        "domain":"x",
        "verified":False,
        "actions":[{"kind":"guess","decision_gain":99,"time":0.1}],
    })
except v2.ActiveTransferLearnerError:
    pass
else:
    raise AssertionError("UNVERIFIED_EPISODE_COMPILED_TO_META_STRATEGY")

# Unknown remains untrusted; full verified coverage can be reused.
episode=v2.learning_episode(
    goal="understand new system",
    required_facts={"mechanism-x"},
    verified_facts=set(),
    hypotheses=[{"id":"h1","plausible":True,"best_action":"inspect"}],
    actions=[{"id":"inspect","decision_gain":1,"transfer_gain":0,"proof_gain":1,"time":1,"cost":0,"risk":0}],
)
assert episode["state"]=="LEARNING"
assert episode["trusted"] is False
assert episode["promotion_authorized"] is False

covered=v2.learning_episode(
    goal="reuse known mechanism",
    required_facts={"mechanism-x"},
    verified_facts={"mechanism-x"},
    hypotheses=[],
    actions=[],
)
assert covered["state"]=="VERIFIED_COVERAGE"
assert covered["trusted"] is True
assert covered["acceptance_credit"] is False
assert covered["ownership_credit"] is False

# Governance boundary.
assert gov["extends_verified_base"]=="canonical/governance/UNIVERSAL_LEARNING_CONTRACT_V1.json"
assert gov["v1_remains_authoritative_for_unknown_capture_and_promotion_safety"] is True
assert gov["acceptance_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["capability_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert "NO_UNIVERSAL_SEMANTIC_SUCCESS_CLAIM" in gov["hard_nonclaims"]
assert "NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT_FROM_V2_ALONE" in gov["hard_nonclaims"]
assert "NO_ABOVE_EXPONENTIAL_GROWTH_GUARANTEE" in gov["hard_nonclaims"]

print(json.dumps({
    "schema":"PROJECT_BRAIN_UNIVERSAL_ACTIVE_TRANSFER_LEARNER_V2_PUBLIC_RUNNER_RESULT_V1",
    "status":"PASS__EXACT_BRAIN_BLOBS__ACTIVE_TRANSFER_OPTIMIZATION_AND_FAIL_CLOSED_BOUNDARIES_VERIFIED__ZERO_CREDIT",
    "pass":True,
    "brain_head_sha":manifest["brain_head_sha"],
    "verified":{
        "exact_brain_blob_identities":True,
        "minimum_novelty_delta":True,
        "decision_value_density_ranking":True,
        "explicit_hypothesis_elimination":True,
        "decision_sufficiency_stopping":True,
        "dependency_cone_invalidation":True,
        "proof_carrying_skill_compilation":True,
        "verified_episode_meta_learning":True,
        "v1_safety_base_preserved":True,
        "zero_credit_boundary_preserved":True
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
