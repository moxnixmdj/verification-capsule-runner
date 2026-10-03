#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import goal_dependency_delta_v4 as delta
from canonical.runtime import open_world_hypothesis_guard_v4 as guard
from canonical.runtime import universal_learning_open_world_router_v4 as router

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/UNIVERSAL_LEARNING_OPEN_WORLD_ROUTER_V4.json").read_text())
assert gov["acceptance_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["capability_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["fresh_reality_authority"] is False
assert "NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT" in gov["hard_nonclaims"]

ENV="env-v4"; GOAL="solve"

def dep_receipt(goals,deps):
    return {
        "receipt_id":"dep","independent_verified":True,"exact_byte_bound":True,
        "conclusion":"success","decision_relevant_dependency_graph_complete":True,
        "environment_id":ENV,"goal_id":GOAL,
        "dependency_graph_sha256":delta.dependency_digest(goals=goals,dependencies=deps),
    }

def cov_receipt(hs):
    return {
        "receipt_id":"cov","independent_verified":True,"exact_byte_bound":True,
        "conclusion":"success","decision_relevant_exhaustive":True,
        "scope_relation":"EXACT","environment_id":ENV,"goal_id":GOAL,
        "hypothesis_space_sha256":guard.hypothesis_digest(hs),
    }

def residual(action):
    return {
        "receipt_id":"res","independent_verified":True,"exact_byte_bound":True,
        "conclusion":"success","all_unmodeled_decision_relevant_alternatives_imply_action":True,
        "environment_id":ENV,"goal_id":GOAL,"action":action,
    }

def safe(aid):
    return {
        "receipt_id":"safe-"+aid,"independent_verified":True,"exact_byte_bound":True,
        "conclusion":"success","safe_under_all_admissible_worlds":True,
        "environment_id":ENV,"goal_id":GOAL,"action_id":aid,
    }

# 1. Proven goal dependency cone removes irrelevant structure and stops at verified boundary.
deps={"solve":["parse","execute"],"parse":["syntax"],"execute":["runtime"],"irrelevant":["noise"]}
out=delta.minimum_goal_delta(
    environment_id=ENV,goal_id=GOAL,goals=["solve"],verified_facts=["parse"],
    dependencies=deps,dependency_receipt=dep_receipt(["solve"],deps),
)
assert out["missing"]==["execute","runtime","solve"],out
assert out["verified_boundary"]==["parse"],out
assert "noise" not in out["missing"]

# 2. Forged dependency receipt cannot shrink learning.
bad=dep_receipt(["solve"],deps)
bad["dependency_graph_sha256"]="sha256:"+"0"*64
try:
    delta.minimum_goal_delta(environment_id=ENV,goal_id=GOAL,goals=["solve"],verified_facts=["parse"],dependencies=deps,dependency_receipt=bad)
except delta.GoalDependencyDeltaError:
    pass
else:
    raise AssertionError("FORGED_DEPENDENCY_RECEIPT_ACCEPTED")

# 3. Cyclic dependency graph fails closed.
cyc={"solve":["x"],"x":["solve"]}
try:
    delta.minimum_goal_delta(environment_id=ENV,goal_id=GOAL,goals=["solve"],verified_facts=[],dependencies=cyc,dependency_receipt=dep_receipt(["solve"],cyc))
except delta.GoalDependencyDeltaError:
    pass
else:
    raise AssertionError("DEPENDENCY_CYCLE_ACCEPTED")

# 4. False consensus over an open hypothesis set is NOT decision sufficient.
hs=[
    {"id":"h1","plausible":True,"best_action":"A","probability":"0"},
    {"id":"h2","plausible":True,"best_action":"A","probability":"999999"},
]
s=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs)
assert s["sufficient"] is False,s
assert "OPEN_WORLD_RESIDUAL" in s["reason"],s

# 5. Every plausible hypothesis counts regardless of declared probability.
hs_disagree=[
    {"id":"h1","plausible":True,"best_action":"A","probability":"0"},
    {"id":"h2","plausible":True,"best_action":"B","probability":"0"},
]
s=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs_disagree,coverage_receipt=cov_receipt(hs_disagree))
assert s["sufficient"] is False,s

# 6. Exact exhaustive coverage permits common-action stopping.
closed=[
    {"id":"h1","plausible":True,"best_action":"A"},
    {"id":"h2","plausible":True,"best_action":"A"},
]
s=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=closed,coverage_receipt=cov_receipt(closed))
assert s["sufficient"] is True and s["open_world_safe"] is True,s

# 7. Residual action invariance can prove sufficiency without enumerating every world.
s=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=closed,residual_action_receipt=residual("A"))
assert s["sufficient"] is True and s["hypothesis_space_closed"] is False,s

# 8. Residual receipt bound to a different action is rejected.
try:
    guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=closed,residual_action_receipt=residual("B"))
except guard.OpenWorldHypothesisError:
    pass
else:
    raise AssertionError("WRONG_ACTION_RESIDUAL_RECEIPT_ACCEPTED")

# 9. Stale hypothesis coverage digest is rejected.
stale=cov_receipt(closed)
stale["hypothesis_space_sha256"]="sha256:"+"0"*64
try:
    guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=closed,coverage_receipt=stale)
except guard.OpenWorldHypothesisError:
    pass
else:
    raise AssertionError("STALE_HYPOTHESIS_COVERAGE_ACCEPTED")

# 10. Minimax probe ranking is independent of arbitrary probability skew.
hs_probe=[
    {"id":"h1","plausible":True,"best_action":"A","probability":"999999999"},
    {"id":"h2","plausible":True,"best_action":"B","probability":"1"},
]
ranked=guard.robust_rank(
    environment_id=ENV,goal_id=GOAL,hypotheses=hs_probe,
    actions=[
        {"id":"useless","outcome_by_hypothesis":{"h1":"same","h2":"same"},"time":1,"safety_receipt":safe("useless")},
        {"id":"split","outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":2,"safety_receipt":safe("split")},
    ],
)
assert [x["id"] for x in ranked["ranked"]]==["split"],ranked
assert ranked["probability_model_required"] is False

# 11. Probe without open-world safety receipt is never executable.
ranked=guard.robust_rank(
    environment_id=ENV,goal_id=GOAL,hypotheses=hs_probe,
    actions=[{"id":"unsafe-unbound","outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":1}],
)
assert ranked["ranked"]==[],ranked
assert ranked["rejected"][0]["id"]=="unsafe-unbound",ranked

# 12. Router conservatively falls back to flat delta without dependency proof.
fallback=router.route(
    goal=GOAL,environment_id=ENV,verified_coverage=False,
    goal_facts=["solve"],fallback_required_facts=["solve","needed","irrelevant","noise"],
    verified_facts=[],dependencies=deps,dependency_receipt=None,transfer_mappings=[],
    hypotheses=closed,hypothesis_coverage_receipt=None,residual_action_receipt=None,actions=[],
)
assert fallback["novelty_delta_kind"]=="CONSERVATIVE_FLAT_FALLBACK",fallback
assert set(fallback["novelty_delta"]["missing"])=={"solve","needed","irrelevant","noise"},fallback
assert fallback["route"]=="ABSTAIN_OR_REQUEST_DISCRIMINATOR",fallback

# 13. Exact goal graph plus safe discriminator produces learning, not false execution.
active=router.route(
    goal=GOAL,environment_id=ENV,verified_coverage=False,
    goal_facts=["solve"],fallback_required_facts=["solve","needed","irrelevant","noise"],
    verified_facts=[],dependencies={"solve":["needed"],"irrelevant":["noise"]},
    dependency_receipt=dep_receipt(["solve"],{"solve":["needed"],"irrelevant":["noise"]}),
    transfer_mappings=[],hypotheses=hs_probe,hypothesis_coverage_receipt=None,
    residual_action_receipt=None,
    actions=[{"id":"probe","outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":1,"safety_receipt":safe("probe")}],
)
assert active["novelty_delta"]["missing"]==["needed","solve"],active
assert active["route"]=="LEARN",active
assert active["next_action"]["id"]=="probe",active
assert active["trusted_execution_authorized"] is False
assert active["promotion_authorized"] is False
assert active["acceptance_credit_delta"]==0
assert active["ownership_credit_delta"]==0

print(json.dumps({
    "schema":"PROJECT_BRAIN_UNIVERSAL_LEARNING_OPEN_WORLD_V4_PUBLIC_RUNNER_RESULT_V1",
    "status":"PASS__EXACT_BLOBS__GOAL_MINIMAL_DELTA__OPEN_WORLD_FALSE_CONSENSUS_BLOCKED__PROBABILITY_FREE_MINIMAX_PROBING__ZERO_CREDIT",
    "pass":True,
    "verified":{
        "exact_brain_blob_identities":True,
        "goal_dependency_delta_requires_complete_bound_graph":True,
        "irrelevant_structure_pruned_only_under_verified_dependency_scope":True,
        "verified_boundary_stops_relearning":True,
        "open_hypothesis_consensus_does_not_stop_learning":True,
        "all_plausible_hypotheses_count_independent_of_probability":True,
        "exhaustive_hypothesis_receipt_enables_safe_sufficiency":True,
        "residual_action_invariance_enables_nonenumerative_sufficiency":True,
        "stale_or_wrong_scope_receipts_rejected":True,
        "probe_requires_open_world_safety_receipt":True,
        "probability_free_minimax_discrimination":True,
        "flat_fallback_preserved_without_dependency_proof":True,
        "zero_terminal_credit_preserved":True
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
