#!/usr/bin/env python3
import copy, hashlib, json, sys
from pathlib import Path

R=Path(__file__).resolve().parent
D=R/"fixtures/synthesis_claim_coverage_ceiling_v2"
EXPECTED={
 "candidate":"f2ef80facb39264b1e12b81e451eb4499a3b987f",
 "historical":"559e1548790af4fccf19150a81419f1d39fa5b8d",
 "historical_failure":"f2c8741a9249b4ad0ae4a82b1ac3f061c882e3e0",
 "semantics":"1a67bc568944212c4d235a463c8bd7bea21b3993",
 "scope_certificate":"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
 "lossless_scope":"1852516f725f5b72badfc2f65be22e542ed83623",
 "scope_activation":"1528485a15c98e89c9fb4dc50d691b6682e08542",
}
TARGET="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
METRIC="required_claim_coverage_noninferiority"
BEHAVIOR="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
FAILS={
 "SOURCE_SCOPE_NOT_PROVED_EXACT_OR_SUPERSET_OF_TARGET_SCOPE",
 "SOURCE_TARGET_SCOPE_RELATION_NOT_INDEPENDENTLY_VERIFIED",
}

def blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_all():
    out={}
    for k,h in EXPECTED.items():
        p=D/(k+".json")
        actual=blob_sha(p)
        if actual!=h:
            raise AssertionError(f"fixture drift {k}: {actual} != {h}")
        out[k]=json.loads(p.read_text())
    return out

def check(d):
    e=[]
    c=d["candidate"]; old=d["historical"]; fail=d["historical_failure"]
    sem=d["semantics"]; cert=d["scope_certificate"]
    loss=d["lossless_scope"]; act=d["scope_activation"]

    if c.get("target_predicate_id")!=TARGET or c.get("target_metric")!=METRIC:
        e.append("CANDIDATE_TARGET_DRIFT")
    auth=c.get("authority") or {}
    expected_auth={
      "historical_candidate":EXPECTED["historical"],
      "historical_independent_failure":EXPECTED["historical_failure"],
      "current_semantics_transport":EXPECTED["semantics"],
      "scope_certificate":EXPECTED["scope_certificate"],
      "lossless_scope_verification":EXPECTED["lossless_scope"],
      "scope_activation_verification":EXPECTED["scope_activation"],
    }
    for k,h in expected_auth.items():
        row=auth.get(k) or {}
        if row.get("git_blob_sha")!=h: e.append("AUTHORITY_HASH_MISMATCH:"+k)

    if fail.get("public_runner",{}).get("conclusion")!="failure":
        e.append("HISTORICAL_FAILURE_RECEIPT_NOT_FAILURE")
    if set(fail.get("failure") or [])!=FAILS:
        e.append("HISTORICAL_FAILURE_NOT_EXACTLY_SCOPE_ONLY")
    if "EXACT_10_OF_10_BRAIN_BLOBS_MATCHED" not in set(fail.get("verified_before_failure") or []):
        e.append("HISTORICAL_EXACT_INPUT_BINDING_MISSING")
    if (fail.get("exact_brain_blobs") or {}).get(
      "canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V1.json"
    )!=EXPECTED["historical"]:
        e.append("HISTORICAL_CANDIDATE_HASH_NOT_BOUND")

    p=old.get("proof") or {}
    expected_old={
      "behavior_id":BEHAVIOR,
      "frozen_oracle_literal":"100_PERCENT_REQUIRED_CLAIM_COVERAGE",
      "brain_required_claim_coverage_lower_bound":1,
      "admissible_metric_upper_bound":1,
      "brain_minus_comparator_lower_bound":0,
      "target_direction":"higher",
      "target_threshold":0,
    }
    for k,v in expected_old.items():
        if p.get(k)!=v: e.append("HISTORICAL_PROOF_DRIFT:"+k)

    sv=sem.get("verified") or {}
    if sv.get("target_predicate_id")!=TARGET or sv.get("v1_to_v3_target_semantics_identical") is not True:
        e.append("TARGET_SEMANTICS_NOT_TRANSPORTED")
    runs=sem.get("independent_runner",{}).get("verification_runs") or []
    if not runs or not all(x.get("conclusion")=="success" for x in runs):
        e.append("SEMANTICS_INDEPENDENT_RUNNER_NOT_GREEN")
    if METRIC not in set(sv.get("missing_metric_bounds") or []):
        e.append("METRIC_NOT_OPEN_BEFORE_LIFT")

    if cert.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR":
        e.append("CERT_TARGET_DRIFT")
    if cert.get("witness_scope_id")!="scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL":
        e.append("CERT_WITNESS_DRIFT")
    if not (cert.get("verified") is True and cert.get("independent") is True):
        e.append("CERT_NOT_VERIFIED_INDEPENDENT")
    if cert.get("scope_relation")!="PROVEN_STRONGER":
        e.append("CERT_RELATION_NOT_STRONGER")
    if not (cert.get("coverage_complete") is True and cert.get("coverage_proof_verified") is True and cert.get("coverage_relation")=="EXACT_UNION"):
        e.append("CERT_COVERAGE_INCOMPLETE")

    lv=loss.get("verified") or {}
    if loss.get("independent_runner",{}).get("conclusion")!="success":
        e.append("LOSSLESS_RUNNER_NOT_GREEN")
    if lv.get("target_predicate_id")!=TARGET or lv.get("scope_relation")!="PROVEN_STRONGER":
        e.append("LOSSLESS_RELATION_INVALID")
    if not (lv.get("exact_dimension_set") is True and lv.get("exact_contract_fragment_witnesses") is True):
        e.append("LOSSLESS_EXACTNESS_MISSING")

    av=act.get("verified") or {}
    if act.get("independent_runner",{}).get("conclusion")!="success":
        e.append("ACTIVATION_RUNNER_NOT_GREEN")
    if av.get("predicate_id")!=TARGET or av.get("after_root_class")!="ROOT2_ONLY":
        e.append("ACTIVATION_TARGET_DRIFT")

    pc=c.get("proof_composition") or {}
    if pc.get("behavior_id")!=BEHAVIOR: e.append("BEHAVIOR_DRIFT")
    if pc.get("source_scope_id")!=cert.get("witness_scope_id") or pc.get("target_scope_id")!=cert.get("target_scope_id"):
        e.append("SCOPE_IDS_NOT_CERT_BOUND")
    if pc.get("verified_source_to_target_relation")!="SUPERSET" or pc.get("relation_independent") is not True:
        e.append("SUPERSET_RELATION_NOT_INDEPENDENT")
    if pc.get("brain_required_claim_coverage_lower_bound")!=1 or pc.get("admissible_metric_upper_bound")!=1:
        e.append("CEILING_NUMBERS_DRIFT")
    if pc.get("brain_minus_comparator_lower_bound")!=0:
        e.append("DERIVED_BOUND_NOT_ZERO")
    if pc.get("target_direction")!="higher" or pc.get("target_threshold")!=0:
        e.append("TARGET_REQUIREMENT_DRIFT")

    bound=(c.get("derived_metric_bounds") or {}).get(METRIC) or {}
    if bound.get("lower")!=0 or bound.get("derivation")!="ABSOLUTE_CEILING_DOMINANCE_AFTER_INDEPENDENT_SUPERSET_SCOPE_REPAIR":
        e.append("DERIVED_BOUND_SHAPE_DRIFT")
    if set(c.get("explicitly_not_proved") or [])!={"metric:matched_quality","matched_quality_noninferiority"}:
        e.append("MATCHED_QUALITY_OVERCLAIM")
    residual=c.get("expected_residual_after_verification") or {}
    if set(residual.get("missing_atoms") or [])!={"metric:matched_quality"}:
        e.append("RESIDUAL_ATOM_DRIFT")
    if set(residual.get("missing_metric_bounds") or [])!={"matched_quality_noninferiority"}:
        e.append("RESIDUAL_BOUND_DRIFT")
    return sorted(set(e))

docs=load_all()
errors=check(docs)
if errors:
    print(json.dumps({"status":"FAIL_CLOSED","errors":errors},indent=2)); sys.exit(1)

# Independent hostile mutations. Each must be rejected.
mutations=[]
x=copy.deepcopy(docs); x["candidate"]["proof_composition"]["verified_source_to_target_relation"]=None; mutations.append(("drop_superset",x))
x=copy.deepcopy(docs); x["historical_failure"]["failure"].append("UNRELATED_PREMISE_FAILURE"); mutations.append(("extra_old_failure",x))
x=copy.deepcopy(docs); x["scope_certificate"]["scope_relation"]="INCOMPARABLE"; mutations.append(("break_scope_relation",x))
x=copy.deepcopy(docs); x["semantics"]["verified"]["v1_to_v3_target_semantics_identical"]=False; mutations.append(("break_semantics",x))
x=copy.deepcopy(docs); x["candidate"]["explicitly_not_proved"]=[]; mutations.append(("matched_quality_overclaim",x))
x=copy.deepcopy(docs); x["candidate"]["proof_composition"]["brain_required_claim_coverage_lower_bound"]=0.99; mutations.append(("lower_brain_bound",x))
mutation_errors=[]
for name,x in mutations:
    if not check(x): mutation_errors.append(name)
if mutation_errors:
    print(json.dumps({"status":"FAIL_CLOSED","mutation_tests_not_rejected":mutation_errors},indent=2)); sys.exit(2)

print(json.dumps({
 "schema":"PROJECT_BRAIN_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_V2_INDEPENDENT_CAPSULE",
 "status":"INDEPENDENT_PASS__REQUIRED_CLAIM_COVERAGE_NONINFERIORITY_GE_0__MATCHED_QUALITY_STILL_OPEN__ZERO_ACCEPTANCE_CREDIT",
 "target_predicate_id":TARGET,
 "metric":METRIC,
 "proof":{"brain_lower_bound":1.0,"any_comparator_upper_bound":1.0,"brain_minus_comparator_lower_bound":0.0},
 "remaining_unproved":["metric:matched_quality","matched_quality_noninferiority"],
 "hostile_mutation_tests_rejected":len(mutations),
 "new_reality_units_consumed":0,"terminal_cases_consumed":0,"incremental_spend_usd":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
 "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
},indent=2,sort_keys=True))
