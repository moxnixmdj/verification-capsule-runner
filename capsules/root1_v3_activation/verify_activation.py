#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MAN=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())

def blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,sha in MAN["candidate_exact_blobs"].items():
    p=ROOT/"candidate"/rel
    assert blob_sha(p)==sha,(rel,blob_sha(p),sha)
for rel,sha in MAN["base_exact_blobs"].items():
    p=ROOT/"base"/rel
    assert blob_sha(p)==sha,(rel,blob_sha(p),sha)

def load(side,rel):
    return json.loads((ROOT/side/rel).read_text())

activation=load("candidate","canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_ACTIVATION_V1.json")
candidate_root=load("candidate","canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
base_root=load("base","canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
gov=load("candidate","canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3.json")
core=load("candidate","canonical/verification/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
audit=load("candidate","canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V1.json")

assert activation["scope"]=="ROOT1_CAPABILITY_MISSING_ONLY"
assert "ACTIVATION_PROJECTION_VERIFICATION_PENDING" in activation["status"]
assert activation["current_root1_truth"]["root1_positive_gap_count"]==0
assert activation["current_root1_truth"]["root1_currently_active"] is False
assert activation["current_root1_truth"]["default_action"]=="NO_ACTION"
assert activation["current_root1_truth"]["verified_owned_family_count"]==5
assert activation["current_root1_truth"]["route_coverage_unproved_family_count"]==14
assert activation["current_root1_truth"]["route_coverage_unproved_is_not_missing"] is True
assert activation["current_root1_truth"]["frozen_opus55_envelope_sealed"] is False

op=activation["operative_control"]
assert op["governance_git_blob_sha"]==MAN["candidate_exact_blobs"]["canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3.json"]
assert op["envelope_audit_git_blob_sha"]==MAN["candidate_exact_blobs"]["canonical/governance/ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V1.json"]
assert op["core_verification_git_blob_sha"]==MAN["candidate_exact_blobs"]["canonical/verification/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]

assert core["independent_verifier"]["conclusion"]=="success"
assert core["verified"]["subject_tests_passed"]=="9/9"
assert core["verified"]["root1_inactive_zero_action"] is True
assert core["verified"]["route_coverage_unproved_not_missing"] is True
assert core["verified"]["exact_minimum_weight_route_cover"] is True
assert core["verified"]["zero_terminal_credit"] is True
assert all(v==0 for v in core["accounting"].values())

assert gov["scope"]=="ROOT1_CAPABILITY_MISSING_ONLY"
assert gov["current_root1_truth"]["root1_positive_gap_count"]==0
assert gov["current_root1_truth"]["root1_currently_active"] is False
assert gov["current_root1_truth"]["root1_frozen_envelope_sealed"] is False
assert all(v==0 for v in gov["accounting"].values())

assert audit["verified_owned_count"]==5
assert audit["route_coverage_unproved_count"]==14
assert audit["classification"]["root1_positive_gap_count"]==0
assert audit["classification"]["route_coverage_unproved_is_capability_missing"] is False

# Candidate authority must differ from the current base only at the Root1 active controller pointer.
c=copy.deepcopy(candidate_root)
b=copy.deepcopy(base_root)
c["roots"]["root_1_capability_missing"]["active_acquisition_control"]=copy.deepcopy(
    b["roots"]["root_1_capability_missing"]["active_acquisition_control"]
)
assert c==b,"CANDIDATE_ROOT_AUTHORITY_CHANGED_OUTSIDE_ROOT1_ACTIVE_CONTROL"

r1=candidate_root["roots"]["root_1_capability_missing"]
assert r1["current_positive_root1_blockers"]==[]
ac=r1["active_acquisition_control"]
assert ac["path"]=="canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_ACTIVATION_V1.json"
assert ac["git_blob_sha"]==MAN["candidate_exact_blobs"]["canonical/governance/ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3_ACTIVATION_V1.json"]
assert ac["current_envelope_sealed"] is False
assert ac["activation_verification"]["status"]=="PENDING_INDEPENDENT_PUBLIC_RUNNER"
assert ac["previous_control"]["status"]=="PRESERVED_VERIFIED_FALLBACK_UNTIL_V3_ACTIVATION_VERIFIED"

assert candidate_root["current_acceptance"]==base_root["current_acceptance"]
assert candidate_root["current_acceptance"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
    "total_families":19,"total_atomic":38,"terminal":False
}
assert candidate_root["scheduler_policy"]["root1_currently_active"] is False
assert candidate_root["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert candidate_root["accounting"]==base_root["accounting"]
assert all(v==0 for v in candidate_root["accounting"].values())

for obj in (activation,core,gov,audit):
    if "accounting" in obj:
        assert all(v==0 for v in obj["accounting"].values())
    for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
        if k in obj:
            assert obj[k] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT1_V3_ACTIVATION_PUBLIC_RUNNER_RESULT",
  "status":"PASS__EXACT_ACTIVATION_PROJECTION__ROOT1_ONLY_DELTA__CORE_VERIFIED__ROOT1_INACTIVE_ZERO_GAPS__5_OWNED_14_ROUTE_UNPROVED_NOT_MISSING__ENVELOPE_UNSEALED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_candidate_blobs":True,
    "exact_base_root_blob":True,
    "candidate_root_diff_is_root1_controller_pointer_only":True,
    "core_independent_verification_bound":True,
    "root1_positive_gap_count_zero":True,
    "root1_inactive":True,
    "inactive_schedules_zero_acquisition":True,
    "declared_family_partition_5_plus_14":True,
    "route_coverage_unproved_not_missing":True,
    "frozen_envelope_unsealed":True,
    "root2_root3_and_terminal_counts_unchanged":True,
    "zero_credit_preserved":True
  },
  "incremental_spend_usd":0,
  "new_reality_units_consumed":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False
},indent=2,sort_keys=True))
