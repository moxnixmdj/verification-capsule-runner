#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_r2e_event_bound_v1"
OUT=ROOT/"root2_r2e_event_bound_v1_receipt.json"

EXPECTED={
  "CANDIDATE.json": "4bcd638848a5d7d87eec77cb98364b3650ff9a49",
  "FRONTIERCODE.json": "26c1f813503c156e818499b2e6fe4fdb00d40c05",
  "GDPVAL_ROUTE.json": "e3d890b0fdfe2c5173cf18efddbc1483b7db6701",
  "GDPVAL_FRESHNESS.json": "d59ec93a0566ccc1982827cbc4b9f92a2c87b248",
  "AUTOMATIONBENCH.json": "3f09067d0fa174c343f2f157495d3654a15b3965",
  "MYSTERY_GATE.json": "44a2f94be04d51773d994741eb3aa6795da92949",
  "MYSTERY_SATURATION.json": "a8b142d5a38683018f0f86d748338b51c9054d02",
  "PARENT_V4.json": "ddebb1ff75f65ee67d444d6f524f3342eecbb519"
}

def blob(p: Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\\0"+b).hexdigest()

def load(name):
    p=SUB/name
    assert blob(p)==EXPECTED[name], (name, blob(p), EXPECTED[name])
    return json.loads(p.read_text(encoding="utf-8"))

c=load("CANDIDATE.json")
f=load("FRONTIERCODE.json")
g=load("GDPVAL_ROUTE.json")
gf=load("GDPVAL_FRESHNESS.json")
a=load("AUTOMATIONBENCH.json")
mg=load("MYSTERY_GATE.json")
ms=load("MYSTERY_SATURATION.json")
p=load("PARENT_V4.json")

assert "R2E_NON_OWNER_CERTIFICATE_AND_BRIDGE_LANE" in p["active_group_ids"]
r2e=[x for x in p["information_positive_now"] if isinstance(x,str)]
# V4 stores atom ids in information_positive_now and group ids separately.
for pred in ["CODING_FRONTIERCODE_GE_54_4","PROWORK_GDPVAL_GE_1846","AUTOMATIONBENCH_GE_40","MYSTERYMECHANISM_GE_49_55"]:
    assert pred in r2e

assert f["verified"]["frontiercode_v1_1_public_exact_self_run"].startswith("NOT_ESTABLISHED")
assert "OWNER_EVALUATION_ACCESS" in f["verified"]["frontiercode_surviving_route"]
assert f["consequence"].startswith("STOP_GENERIC_PUBLIC_SELF_RUN_SEARCH")

assert g["verified"]["pairwise_elo_reproduction_complete"] is False
assert g["verified"]["owner_judge_panel_graph_crowd_bt_and_anchor_still_required"] is True
assert "PAIRWISE_ELO_OWNER_LAYER" in g["consequence"]
assert gf["current_truth"]["gdpval_predicate_proved"] is False
assert gf["current_truth"]["current_owner_epoch_target_elo"]==1867
assert gf["current_truth"]["legacy_historical_target_elo"]==1846

assert a["deduction"]["public_600_is_official_leaderboard_population"] is False
assert a["deduction"]["public_600_score_is_guaranteed_equal_to_private_leaderboard_score"] is False
assert a["deduction"]["public_600_score_can_directly_discharge_private_bar_without_scope_equivalence_proof"] is False

assert mg["deduction"]["current_predicate_state"]=="EXTERNAL_REQUIRED__NOT_PROVED"
assert ms["search_result"]["exhaustive_private_mechanism_generator_published"] is False
assert ms["search_result"]["exhaustive_symbolic_grammar_published"] is False
assert ms["search_result"]["public_source_proves_current_brain_symbolic_grammar_covers_at_least_the_required_private_success_mass"] is False
assert ms["search_result"]["bounded_absence_only"] is True

rows={x["predicate"]:x for x in c["predicate_reclassification"]}
expected={
 "CODING_FRONTIERCODE_GE_54_4":"EVENT_OR_STRONGER_PROOF_BOUND",
 "PROWORK_GDPVAL_GE_1846":"OWNER_RELATIVE_SCORE_LAYER_OR_STRONGER_PROOF_BOUND",
 "AUTOMATIONBENCH_GE_40":"PRIVATE_POPULATION_RELATION_OR_STRONGER_PROOF_BOUND",
 "MYSTERYMECHANISM_GE_49_55":"PRIVATE_SCORE_OR_SCOPE_SUPERSET_EVENT_BOUND",
}
assert set(rows)==set(expected)
for k,v in expected.items():
    assert rows[k]["current_state"]==v
assert c["scheduler_delta"]["parent_active_group_count"]==6
assert c["scheduler_delta"]["candidate_active_group_count"]==5
assert c["scheduler_delta"]["sleep_group"]=="R2E_NON_OWNER_CERTIFICATE_AND_BRIDGE_LANE"
assert set(c["scheduler_delta"]["preserve_open_predicates"])==set(expected)
assert c["accounting"]=={
 "incremental_spend_usd":0,
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0
}
assert c["execution_authority"] is False
assert c["promotion_authority"] is False
assert c["fresh_reality_authority"] is False

receipt={
 "schema":"PROJECT_BRAIN_ROOT2_R2E_EVENT_BOUND_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__R2E_FOUR_OPEN_PREDICATES_EVENT_BOUND__ACTIVE_GROUP_6_TO_5_SCHEDULING_ONLY__ZERO_CREDIT",
 "subject_blob_sha":EXPECTED["CANDIDATE.json"],
 "verified":{
   "frontiercode_generic_public_route_saturated":True,
   "gdpval_owner_relative_layer_required":True,
   "automationbench_public_private_substitution_blocked":True,
   "mysterymechanism_public_scope_superset_search_saturated_current_sources":True,
   "all_four_predicates_preserved_open":True,
   "parent_active_groups":6,
   "candidate_active_groups":5
 },
 "authority":{"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False},
 "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
