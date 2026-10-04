#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_root1_revocation_v1"
EXPECTED={
 "LIVEBENCH_ROOT1_REVOCATION_TRUTH_REPAIR_V1.json":"219f1b4c508f659620feea3de1295e3edad102a7",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"c3d1e25e2268cce90df545a93f107aa24fed8f8b",
 "LIVEBENCH_LOCAL_ROOT_RECLASSIFICATION_V1.json":"eef18a73b23db53082b934976bcbd05cab9c5684",
 "LIVEBENCH_ROOT_PARTITION_PROJECTION_V1.json":"21dc5e07e18ba3e99a97ffef20a098833c684e99",
 "LIVEBENCH_PARTIAL_CREDIT_UPPER_BOUND_TRUTH_REPAIR_20261004_V1.json":"359f740191e528f16b30ed6b893dad5caee5698d",
 "livebench_partial_credit_mass_v1.py":"0e3c0d89736d809f5378a3c81734eb4295b48ce2",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for name,sha in EXPECTED.items():
 data=(SUB/name).read_bytes()
 assert blob(data)==sha,(name,blob(data),sha)

candidate=json.loads((SUB/"LIVEBENCH_ROOT1_REVOCATION_TRUTH_REPAIR_V1.json").read_text())
root=json.loads((SUB/"TERMINAL_ROOT_CAUSE_STATE_V1.json").read_text())
old=json.loads((SUB/"LIVEBENCH_LOCAL_ROOT_RECLASSIFICATION_V1.json").read_text())
proj=json.loads((SUB/"LIVEBENCH_ROOT_PARTITION_PROJECTION_V1.json").read_text())
repair=json.loads((SUB/"LIVEBENCH_PARTIAL_CREDIT_UPPER_BOUND_TRUTH_REPAIR_20261004_V1.json").read_text())

# Recompute the exact logical failure that powered the Root2 -> Root1 move.
assert old["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert old["evidence"]["verified_observed_zero_score_cases"]==72
assert old["evidence"]["population_count"]==200
assert old["evidence"]["maximum_remaining_score_mass"]==128
assert old["evidence"]["full_population_upper_percent"]==64
assert old["root_transition"]["prior_local_class"].startswith("ROOT2_ONLY")
assert old["root_transition"]["new_local_class"].startswith("ROOT1_")

# The active truth repair explicitly revokes treating lower-bound zero as score upper-bound zero.
assert repair["status"].startswith("ACTIVE_TRUTH_REPAIR__UNSOUND_FORCED_FAIL_INFERENCE_REMOVED")
assert repair["bug"]["logical_error"]=="LOWER_BOUND_EVIDENCE_DOES_NOT_IMPLY_EXACTNESS_OR_AN_UPPER_BOUND"
assert repair["repair"]["default_case_score_upper_bound"]==1.0

# Execute the repaired bound calculator.
spec=importlib.util.spec_from_file_location("lbmass",SUB/"livebench_partial_credit_mass_v1.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows=[mod.CaseBound(1,0,False) for _ in range(72)]
cert=mod.aggregate_certificate(rows)
assert cert["full_population_score_mass_upper_bound"]==200.0
assert cert["forced_fail"] is False
# Separate exact upper-bound evidence WOULD support the old 128/64 logic, proving
# the distinction is evidentiary rather than arithmetic.
rows_exact=[mod.CaseBound(1,0,False,proved_score_upper_bound=0.0) for _ in range(72)]
cert_exact=mod.aggregate_certificate(rows_exact)
assert cert_exact["full_population_score_mass_upper_bound"]==128.0
assert cert_exact["forced_fail"] is True

# Current Root1 authority contains one positive blocker and it is the revoked
# LiveBench forced-fail route. No other positive Root1 blocker is bound here.
r1=root["roots"]["root_1_capability_missing"]
blockers=r1["current_positive_root1_blockers"]
assert len(blockers)==1
assert blockers[0]["predicate_id"]=="LIVEBENCH_IF_GE_65_7"
assert blockers[0]["forced_fail_binding"]=="canonical/governance/LIVEBENCH_V6_FORCED_FAIL_BINDING_V1.json"
assert "UNKNOWN_OR_UNPROVED_CAPABILITY_MUST_NOT_BE_CLASSIFIED_AS_MISSING" in r1["classification_rule"]

p=root["current_residual_root_partition"]
assert p["root1_positive_gap_count"]==1
assert p["root2_only_count"]==15
assert p["root3_only_count"]==7
assert p["root2_and_root3_count"]==3
assert p["root1_only"]==["LIVEBENCH_IF_GE_65_7"]
assert "UNKNOWN_OR_UNMEASURED_FIXED_BAR=>ROOT2" in p["derivation_rule"]
assert "PROVED_FALSE_FIXED_BAR_WITH_CONSTRUCTIVE_OPERATIVE_SYSTEM_FAILURE=>ROOT1" in p["derivation_rule"]

# The old projection itself preserves the exact pre-Root1 partition to restore.
assert proj["before"]["root1_only_count"]==0
assert proj["before"]["root2_only_count"]==16
assert "LIVEBENCH_IF_GE_65_7" in proj["before"]["root2_only"]
assert proj["after"]["root1_only"]==["LIVEBENCH_IF_GE_65_7"]

after=candidate["exact_partition_repair"]["after"]
assert after["unresolved_total"]==26
assert after["root1_only_count"]==0
assert after["root2_only_count"]==16
assert after["root3_only_count"]==7
assert after["root2_and_root3_count"]==3
assert after["root2_touching_count"]==19
assert after["livebench_membership"]=="ROOT2_ONLY"
assert after["root1_only_count"]+after["root2_only_count"]+after["root3_only_count"]+after["root2_and_root3_count"]==26

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_ROOT1_REVOCATION_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS",
 "subject_git_blobs":EXPECTED,
 "verified":{
   "old_root1_transition_depends_on_72_case_forced_fail_upper_bound":True,
   "active_truth_repair_revokes_lower_bound_as_upper_bound_inference":True,
   "repaired_72_case_conservative_upper_mass":cert["full_population_score_mass_upper_bound"],
   "repaired_72_case_forced_fail":cert["forced_fail"],
   "explicit_zero_upper_bound_control_forced_fail":cert_exact["forced_fail"],
   "current_root1_authority_has_no_second_positive_blocker":True,
   "classification_rule_returns_unknown_fixed_bar_to_root2":True,
   "restored_partition":{"root1_only":0,"root2_only":16,"root3_only":7,"root2_and_root3":3,"root2_touching":19},
   "acceptance_credit_delta":0,
   "terminal_cases_consumed":0
 },
 "deduction":"THE_CURRENT LIVEBENCH ROOT1 POSITIVE-GAP ACTIVATION HAS LOST ITS LOAD-BEARING PREMISE. UNDER THE BOUND ROOT CLASSIFICATION RULE, LIVEBENCH_IF_GE_65_7 RETURNS FAIL-CLOSED TO ROOT2_ONLY UNTIL A SOUND VALUE OR OTHER POSITIVE OPERATIVE-GAP PROOF EXISTS.",
 "hard_nonclaims":["NO_CLAIM_LIVEBENCH_PASSES","NO_ACCEPTANCE_CREDIT","NO_FRESH_REALITY","NO_CLAIM_NO_FUTURE_ROOT1_PROOF_CAN_EXIST"]
}
(ROOT/"livebench_root1_revocation_verification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
