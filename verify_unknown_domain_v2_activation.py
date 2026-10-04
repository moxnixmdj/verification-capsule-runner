from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_CANDIDATE_V1.json":"1d05dc42fc34b1d97d3d6c12addfe690f475a505",
 "canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"36452412fb60ce38405f139111eba98b5cebc040",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PRECOMMIT_V1.json":"ddf55f3e54ef6af89a95395075441742cb124258",
 "canonical/runtime/unknown_domain_direct_production_preflight_v1.py":"e1365ccdba308c529f182797cf68075b2f1dc07c",
 "canonical/tests/test_unknown_domain_direct_production_preflight_v1.py":"c81a5a16b99cbaf4ae5f8d26f173a18f0da20928",
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/tests/test_unknown_domain_direct_candidate_v2.py":"a56e7fcaa985a1cf1a573166843816c42fa943df",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PREEXPOSURE_V1.json":"77018decd79e13168d14e2e5ed6ee319fa79d83c",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_QUALIFICATION_V1.json":"a3574e1b8b2c33c0265c018dbb4872410e41de24",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json":"6bf6042a7a36c12d6d5ebfc5d16ea23ed2befbb6",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json":"3e3a87962c13ad4c76621508763fab74df25cb44",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"3fd35b7865f7827a5a7b4202bc625fe0f980dcda",
 "canonical/governance/H100_CURRENT_RESEARCH_FRONTIER_V1.json":"4584299538446c9fe5397a646ccce99efa5ba950",
 "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"11498bd194c8018617767918edec020268239bc1"
}

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel,expected in EXPECTED.items():
 got=blob((ROOT/rel).read_bytes())
 assert got==expected,(rel,got,expected)

act=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_CANDIDATE_V1.json").read_text())
rec=json.loads((ROOT/"canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
root=json.loads((ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
front=json.loads((ROOT/"canonical/governance/H100_CURRENT_RESEARCH_FRONTIER_V1.json").read_text())
matrix=json.loads((ROOT/"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json").read_text())

assert act["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert act["authorized_predicates"]==["UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
assert set(act["authorized_leaves"])=={
 "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
 "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
}
assert act["authority"]=={
 "execution":False,
 "predicate_local_fresh_reality":False,
 "global_fresh_reality":False,
 "promotion":False,
 "acceptance_credit":False
}
cond=act["conditional_authority_if_independently_verified"]
assert cond["execution"] is True
assert cond["predicate_local_fresh_reality"] is True
assert cond["global_fresh_reality"] is False
assert cond["promotion"] is False
assert cond["acceptance_credit"] is False
assert cond["all_other_unresolved_predicates_authorized"] is False
assert act["production_budget"]["production_populations_allowed"]==1
assert act["production_budget"]["production_cases_allowed"]==27
assert act["production_budget"]["production_cases_consumed_before_activation"]==0
assert act["production_budget"]["replay_allowed"] is False
assert act["production_budget"]["replacement_allowed"] is False
assert act["resource_boundary"]=={
 "persistent_learned_bytes":0,
 "external_frontier_model_calls":0,
 "external_learned_capability_calls":0,
 "incremental_spend_usd":0
}
assert rec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert rec["verified_result"]["fresh_hidden_scored_cases"]==81
assert rec["verified_result"]["all_fresh_cases_pass"] is True
assert rec["verified_result"]["max_transfer_probes"]==2
assert rec["verified_result"]["persistent_learned_bytes"]==0
assert rec["verified_result"]["production_cases_generated"]==0
assert root["schema"]=="PROJECT_BRAIN_TERMINAL_ROOT_CAUSE_STATE_V1"
assert front["terminal_truth"]["h100_closed"] is False
rows=matrix.get("families",matrix.get("capability_families",[]))
if rows:
 ud=[x for x in rows if x.get("family")=="UNKNOWN_DOMAIN_ADAPTATION"]
 assert len(ud)==1 and ud[0].get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER"

subprocess.check_call(["python","-m","unittest","canonical.tests.test_unknown_domain_direct_candidate_v2","-v"])
subprocess.check_call(["python","-m","unittest","canonical.tests.test_unknown_domain_direct_production_preflight_v1","-v"])
print(json.dumps({
 "status":"INDEPENDENT_UNKNOWN_DOMAIN_V2_ACTIVATION_CANDIDATE_PASS",
 "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
 "qualified_fresh_cases":81,
 "persistent_learned_bytes":0,
 "production_cases_consumed":0,
 "conditional_predicate_local_fresh_reality":True,
 "global_fresh_reality":False,
 "promotion":False,
 "acceptance_credit":False
},indent=2,sort_keys=True))
