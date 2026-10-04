#!/usr/bin/env python3
import json, pathlib, subprocess

BASE=pathlib.Path("subject/authority_root_projection_20261004_sol")
AUTH=BASE/"AUTHORITY.json"
ROOT=BASE/"ROOT_STATE.json"

EXPECTED_AUTH="1859f9775158c827f8209d416327ee152bef78a1"
EXPECTED_ROOT="9ac3c636b2ed76c7f4b1c7cfd8e2762bc7230d0c"
REL_ACT="5edaf436becf45c8d8f3477ac7a53a1e8ac3a63a"
REL_VER="b6daf8b1892a8dc11020b6c5a4102b1fed256240"
SYN_ACT="300fb663e6b598b389961ddf663d88abcd206545"
SYN_VER="e13360b7aba2756f0eb97cac977515c07f3bcbdc"

def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()

assert blob(AUTH)==EXPECTED_AUTH,(blob(AUTH),EXPECTED_AUTH)
assert blob(ROOT)==EXPECTED_ROOT,(blob(ROOT),EXPECTED_ROOT)

a=json.loads(AUTH.read_text())
r=json.loads(ROOT.read_text())

assert a["truth"]=={
    "terminal_execution":"3352/3352_RAW_EXECUTIONS_PASS__IMMUTABLE",
    "contracts":"12/12_WHOLE_SCOPE_PASS__P1_SCOPE_RESTORED_BY_INDEPENDENT_ZERO_REALITY_UNIVERSAL_PROOF",
    "behavioral_families":"19/19_PROVISIONAL_BEHAVIORAL_PASS__P1_SCOPE_QUARANTINE_CLEARED__STRICT_OPUS55_ACCEPTANCE_SEPARATE",
    "opus55_acceptance":"5/19_PASS__14/19_OPEN",
    "global_postconditions":"INDEPENDENT_PASS",
    "donor_cleanroom":"INDEPENDENT_PASS",
    "achieved":False,
    "opus55_verified_owned":"5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN",
}

for key in ("terminal_root_cause_state","terminal_root_cause_state_v1"):
    p=a["sources"][key]
    assert p["path"]=="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
    assert p["git_blob_sha"]==EXPECTED_ROOT,(key,p["git_blob_sha"])

assert r["current_acceptance"]=={
    "accepted_families":5,
    "open_families":14,
    "proved_atomic":12,
    "unresolved_atomic":26,
    "total_families":19,
    "total_atomic":38,
    "terminal":False,
}

part=r["current_residual_root_partition"]
assert (part["root1_positive_gap_count"],part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(0,16,7,3)

rel=r["scheduler_policy"]["relative_elo_absolute_proof_nontransport"]
assert rel["activation_git_blob_sha"]==REL_ACT
assert rel["verification_git_blob_sha"]==REL_VER
assert rel["affected_predicate_count"]==3
assert set(rel["affected_predicates"])=={
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}
assert rel["execution_authority"] is False
assert rel["promotion_authority"] is False
assert rel["fresh_reality_authority"] is False

syn=r["scheduler_policy"]["synthesis_dimension_scorers_and_strict_reducer"]
assert syn["activation_git_blob_sha"]==SYN_ACT
assert syn["verification_git_blob_sha"]==SYN_VER
assert syn["target_predicate"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert set(syn["deleted_residuals"])=={
    "FIVE_CASE_SPECIFIC_QUALITY_DIMENSION_SCORER_BINDINGS_UNSPECIFIED",
    "PORTFOLIO_LEVEL_CONSERVATIVE_MATCHED_NONINFERIORITY_REDUCER_UNSPECIFIED",
}
assert syn["execution_authority"] is False
assert syn["promotion_authority"] is False
assert syn["fresh_reality_authority"] is False

assert r["accounting"]=={
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0,
    "new_reality_units_consumed":0,
    "incremental_spend_usd":0,
}

print("PASS: current authority points to exact combined verified root state")
print("PASS: terminal truth remains 5/19 accepted, 12/38 proved, 26 unresolved")
print("PASS: relative-Elo pruning and synthesis scorer/reducer freeze are active zero-credit reductions")
print("PASS: no execution, promotion, or fresh-reality authority granted by either reduction")
