#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
M=json.loads((R/"EXPECTED.json").read_text())
def sha(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
ap=R/"candidate/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_ACTIVATION_V1.json"
cp=R/"candidate/TERMINAL_ROOT_CAUSE_STATE_V1.json"
bp=R/"base/TERMINAL_ROOT_CAUSE_STATE_V1.json"
assert sha(ap)==M["candidate_activation_blob"]
assert sha(cp)==M["candidate_root_blob"]
assert sha(bp)==M["base_root_blob"]
a=json.loads(ap.read_text()); c=json.loads(cp.read_text()); b=json.loads(bp.read_text())
assert a["status"]=="ACTIVE_MAIN_CANDIDATE__CORE_INDEPENDENT_PUBLIC_RUNNER_PASS__ROOT1_INACTIVE__ZERO_CREDIT"
assert a["scope"]=="ROOT1_CAPABILITY_MISSING_ONLY"
assert a["current_root1_truth"]=={
 "root1_positive_gap_count":0,"root1_currently_active":False,"default_action":"NO_ACTION",
 "declared_terminal_family_count":19,"verified_owned_family_count":5,
 "route_coverage_unproved_family_count":14,"route_coverage_unproved_is_not_missing":True,
 "frozen_opus55_envelope_sealed":False}
assert a["operative_control"]["core_verification_git_blob_sha"]==M["core_verification_blob"]
assert a["operative_control"]["core_verifier_pull_request"]==1524
assert a["operative_control"]["core_workflow_run_id"]==37164893100
assert all(v==0 for v in a["accounting"].values())
assert a["execution_authority"] is False and a["promotion_authority"] is False and a["fresh_reality_authority"] is False
assert "NO_CLAIM_THAT_ALL_WORLD_DATA_IS_REACHABLE" in a["preserved_nonclaims"]

r1=c["roots"]["root_1_capability_missing"]; ac=r1["active_acquisition_control"]
assert r1["current_positive_root1_blockers"]==[]
assert ac["git_blob_sha"]==M["candidate_activation_blob"]
assert ac["status"].startswith("ACTIVE_MAIN_CANDIDATE__CORE_INDEPENDENT_PUBLIC_RUNNER_PASS")
assert ac["current_envelope_sealed"] is False
assert ac["activation_verification"]["status"]=="PENDING_FINAL_INDEPENDENT_PUBLIC_RUNNER"
assert ac["previous_control"]["status"]=="PRESERVED_VERIFIED_FALLBACK_UNTIL_V3_ACTIVATION_VERIFIED"

cc=copy.deepcopy(c); bb=copy.deepcopy(b)
cc["roots"]["root_1_capability_missing"]["active_acquisition_control"]=copy.deepcopy(
 bb["roots"]["root_1_capability_missing"]["active_acquisition_control"])
assert cc==bb,"FINAL_CANDIDATE_CHANGED_NON_ROOT1_AUTHORITY"
assert c["current_acceptance"]==b["current_acceptance"]
assert c["scheduler_policy"]["root1_currently_active"] is False
assert c["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert c["accounting"]==b["accounting"] and all(v==0 for v in c["accounting"].values())
print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT1_V3_FINAL_ACTIVATION_PUBLIC_RUNNER_RESULT",
 "status":"PASS__FINAL_EXACT_ACTIVATION_BLOB__ROOT1_ONLY_AUTHORITY_DELTA__ROOT1_INACTIVE_ZERO_GAPS__ENVELOPE_UNSEALED__COUNTS_UNCHANGED__ZERO_CREDIT",
 "pass":True,
 "verified":{"exact_final_activation_blob":True,"exact_candidate_root_blob":True,"root1_only_authority_delta":True,
 "core_verification_bound":True,"root1_zero_gaps":True,"root1_inactive":True,"zero_acquisition_default":True,
 "five_owned_fourteen_unproved_not_missing":True,"envelope_unsealed":True,"terminal_counts_unchanged":True,"zero_credit":True},
 "incremental_spend_usd":0,"new_reality_units_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
 "fresh_reality_authority":False},indent=2,sort_keys=True))
