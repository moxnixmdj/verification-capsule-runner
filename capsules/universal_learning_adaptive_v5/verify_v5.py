#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,sys
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import open_world_hypothesis_guard_v4 as v4
from canonical.runtime import verified_probe_model_v5 as model
from canonical.runtime import adaptive_experiment_planner_v5 as planner
from canonical.runtime import universal_learning_adaptive_router_v5 as router

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/UNIVERSAL_LEARNING_ADAPTIVE_ROUTER_V5.json").read_text())
assert gov["acceptance_credit_delta"]==0
assert gov["ownership_credit_delta"]==0
assert gov["fresh_reality_authority"] is False

ENV="env-v5";GOAL="solve"
HS=[
 {"id":"h1","plausible":True,"best_action":"A"},
 {"id":"h2","plausible":True,"best_action":"A"},
 {"id":"h3","plausible":True,"best_action":"B"},
 {"id":"h4","plausible":True,"best_action":"B"},
]
def cov():
    return {"receipt_id":"cov","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_exhaustive":True,"scope_relation":"EXACT","environment_id":ENV,"goal_id":GOAL,"hypothesis_space_sha256":v4.hypothesis_digest(HS)}
def safe(aid):
    return {"receipt_id":"safe-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","safe_under_all_admissible_worlds":True,"environment_id":ENV,"goal_id":GOAL,"action_id":aid}
def probe(aid,outcomes,cost):
    return {"id":aid,"outcome_by_hypothesis":outcomes,"time":cost,"safety_receipt":safe(aid),"outcome_model_receipt":{"receipt_id":"model-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_outcome_partition_complete":True,"environment_id":ENV,"goal_id":GOAL,"action_id":aid,"hypothesis_space_sha256":v4.hypothesis_digest(HS),"outcome_map_sha256":model.outcome_digest(action_id=aid,outcomes=outcomes)}}
PROBES=[
 probe("direct",{"h1":"a","h2":"a","h3":"b","h4":"b"},5),
 probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1),
 probe("y",{"h1":"u","h2":"v","h3":"v","h4":"u"},1),
]

# Receipt-bound outcome models are load-bearing.
tampered=probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1)
tampered["outcome_by_hypothesis"]["h4"]="tampered"
try: model.admit(environment_id=ENV,goal_id=GOAL,hypotheses=HS,probe=tampered)
except model.VerifiedProbeModelError: pass
else: raise AssertionError("TAMPERED_OUTCOME_MODEL_ACCEPTED")

# V4's one-step action-class heuristic chooses the direct split (cost 5).
v4rank=v4.robust_rank(environment_id=ENV,goal_id=GOAL,hypotheses=HS,actions=[
 {"id":"direct","outcome_by_hypothesis":PROBES[0]["outcome_by_hypothesis"],"time":5,"safety_receipt":safe("direct")},
 {"id":"x","outcome_by_hypothesis":PROBES[1]["outcome_by_hypothesis"],"time":1,"safety_receipt":safe("x")},
 {"id":"y","outcome_by_hypothesis":PROBES[2]["outcome_by_hypothesis"],"time":1,"safety_receipt":safe("y")},
])
assert v4rank["ranked"][0]["id"]=="direct",v4rank

# Independent exhaustive DP over the same finite verified experiment model.
best_action={h["id"]:h["best_action"] for h in HS}
outcomes={p["id"]:p["outcome_by_hypothesis"] for p in PROBES}
costs={p["id"]:Fraction(str(p["time"])) for p in PROBES}
@lru_cache(None)
def brute(state,remaining):
    state=frozenset(state)
    acts={best_action[h] for h in state}
    if len(acts)==1:return Fraction(0)
    best=None
    for pid in remaining:
        groups={}
        for h in state: groups.setdefault(outcomes[pid][h],set()).add(h)
        if len(groups)<=1:continue
        rem=tuple(x for x in remaining if x!=pid)
        children=[]
        for group in groups.values():
            c=brute(tuple(sorted(group)),rem)
            if c is None:break
            children.append(c)
        else:
            total=costs[pid]+max(children)
            if best is None or total<best:best=total
    return best
independent_optimum=brute(tuple(sorted(best_action)),tuple(sorted(outcomes)))
assert independent_optimum==Fraction(2),independent_optimum

out=planner.plan(environment_id=ENV,goal_id=GOAL,hypotheses=HS,hypothesis_coverage_receipt=cov(),probes=PROBES)
assert out["status"]=="VERIFIED_MINIMUM_WORST_CASE_ADAPTIVE_PLAN",out
assert Fraction(out["worst_case_cost"])==independent_optimum,out
assert out["worst_case_steps"]==2,out
assert out["recommended_probe"] in {"x","y"},out

# No verified model, no pretend information gain.
bad=probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1)
bad["outcome_model_receipt"]["outcome_map_sha256"]="sha256:"+"0"*64
r=router.route(goal=GOAL,environment_id=ENV,verified_coverage=False,goal_facts=["solve"],fallback_required_facts=["solve"],verified_facts=[],dependencies={},dependency_receipt=None,transfer_mappings=[],hypotheses=HS,hypothesis_coverage_receipt=cov(),residual_action_receipt=None,probes=[bad])
assert r["route"]=="ABSTAIN_OR_REQUEST_VERIFIED_MODEL",r
assert r["acceptance_credit_delta"]==0
assert r["ownership_credit_delta"]==0
assert r["fresh_reality_authority"] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_UNIVERSAL_LEARNING_ADAPTIVE_V5_PUBLIC_RUNNER_RESULT_V1",
 "status":"PASS__EXACT_BLOBS__OUTCOME_MODEL_BINDING__INDEPENDENT_ADAPTIVE_OPTIMALITY__GREEDY_TRAP_ELIMINATED__ZERO_CREDIT",
 "pass":True,
 "verified":{
   "exact_brain_blob_identities":True,
   "tampered_outcome_models_rejected":True,
   "v4_greedy_direct_cost_five_reproduced":True,
   "independent_exhaustive_optimum_cost_two":True,
   "v5_planner_matches_independent_optimum":True,
   "unverified_information_gain_rejected":True,
   "probability_free_adaptive_planning":True,
   "zero_terminal_credit_preserved":True
 },
 "new_reality_units_consumed":0,"incremental_spend_usd":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
 "execution_authority":False,"promotion_authority":False
},indent=2,sort_keys=True))
