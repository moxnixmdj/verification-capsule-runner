from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FILES={
"candidate":"canonical/governance/COMPOSITION_BRIDGE_SCOPE_FIREWALL_RECONCILIATION_V1.json",
"bridge":"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json",
"activation":"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json",
"slice":"canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261002_V2.json",
"firewall":"canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json",
"bindings":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"}
SHA={
FILES["candidate"]:"6bdcc7376125d9d4c1bf7f7771630634a342d4e5",
FILES["bridge"]:"d6cb17f548493e64ca3d200d51b049412a939ef7",
FILES["activation"]:"59504f4608f9490022c1aa58214e34191fb0b6e9",
FILES["slice"]:"714d1771ad2fa3ca240c0fb73609dc4873ea4390",
FILES["firewall"]:"ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
FILES["bindings"]:"af83f4899169e81017767c3316ddcf6b61da5ef6"}
RULE="THE_SOURCE_FAMILY_CLOSURE_MUST_BE_VERIFIED_INDEPENDENT_CONTAMINATION_CLEAN_BIND_THE_FROZEN_PROTOCOL_BE_PROVEN_STRONGER_AND_CLOSE_THE_ENTIRE_PROTOCOL"

def blob(b):
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def load(k):
    p=ROOT/FILES[k]; b=p.read_bytes()
    assert blob(b)==SHA[FILES[k]], (k,blob(b),SHA[FILES[k]])
    return json.loads(b)
def fail(cond,msg,errs):
    if not cond: errs.append(msg)

def evaluate(d):
    c,b,a,s,f,e=d["candidate"],d["bridge"],d["activation"],d["slice"],d["firewall"],d["bindings"]
    errs=[]
    fail(RULE in b.get("derivation_rules",[]),"BRIDGE_WHOLE_PROTOCOL_CLOSURE_RULE_MISSING",errs)
    expected={
      "TOOL_DISCOVERY_SELECTION_AND_LEARNING":("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR","tool discovery"),
      "SUBAGENT_DELEGATION_AND_COORDINATION":("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR","delegation")}
    bridge_fams={x.get("source_family"):x for x in b.get("bindings",[])}
    act_fams={x.get("source_family"):x for x in a.get("receipts",[])}
    for fam,(pred,component) in expected.items():
        fail(fam in bridge_fams,f"BRIDGE_SOURCE_MISSING:{fam}",errs)
        fail(fam in act_fams,f"ACTIVATED_RECEIPT_MISSING:{fam}",errs)
        rows=[x for x in e.get("claims",[]) if x.get("predicate_id")==pred]
        fail(len(rows)==1,f"CURRENT_PREDICATE_NOT_UNIQUE:{pred}",errs)
        if len(rows)==1:
            fail(rows[0].get("state")=="EXTERNAL_BLOCKED",f"PREDICATE_NOT_BLOCKED:{pred}",errs)
            fail(rows[0].get("blocker")=="ABSOLUTE_SCOPE_COMPLETENESS_MISSING",f"WRONG_BLOCKER:{pred}",errs)
            fail(rows[0].get("family")==fam,f"PREDICATE_FAMILY_MISMATCH:{pred}",errs)
        stale=[x for x in c.get("stale_receipts",[]) if x.get("source_family")==fam]
        fail(len(stale)==1,f"CANDIDATE_STALE_ROW_MISSING:{fam}",errs)
        if len(stale)==1:
            fail(stale[0].get("component_id")==component,f"STALE_COMPONENT_MISMATCH:{fam}",errs)
            fail(stale[0].get("current_source_acceptance_predicate")==pred,f"STALE_PREDICATE_MISMATCH:{fam}",errs)
            fail(stale[0].get("effect")=="QUARANTINE_FROM_CURRENT_COMPOSITION_SCOPED_PROOF",f"STALE_EFFECT_INVALID:{fam}",errs)
    exp=f.get("expected_current_reduction",{})
    fail(exp.get("closed_family_count")==2,"FIREWALL_CLOSED_COUNT_NOT_2",errs)
    fail(set(exp.get("reopened_pending_scope_completeness",[]))==set(expected),"FIREWALL_REOPENED_SET_MISMATCH",errs)
    fail(set(exp.get("preserved_closed_families",[]))=={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"},"PRESERVED_CLOSED_SET_MISMATCH",errs)
    proved={x.get("component_id") for x in s.get("interfaces",[]) if x.get("state")=="SCOPED_PROVED"}
    fail(proved=={"tool discovery","delegation"},"V2_SLICE_PROVED_SET_UNEXPECTED",errs)
    corr=c.get("corrected_composition_component_state_before_any_new_receipt",{})
    fail(corr.get("scoped_proved_interface_count")==0 and corr.get("open_interface_count")==12,"CORRECTED_COUNTS_INVALID",errs)
    fail(corr.get("parent_predicate_closed") is False,"PARENT_MUST_REMAIN_OPEN",errs)
    fail(c.get("new_reality_units_consumed")==0 and c.get("incremental_spend_usd")==0,"NONZERO_REALITY_OR_SPEND",errs)
    fail(c.get("capability_credit_delta")==0 and c.get("family_credit_delta")==0,"NONZERO_CREDIT",errs)
    fail(c.get("execution_authority") is False and c.get("promotion_authority") is False,"AUTHORITY_MUST_BE_FALSE",errs)
    return errs

def main():
    d={k:load(k) for k in FILES}
    errs=evaluate(d)
    if errs:
        print(json.dumps({"status":"FAIL","errors":errs},indent=2)); return 1
    # Counterfactual: if both source predicates were current PROVED, quarantine is not derivable.
    import copy
    d2=copy.deepcopy(d)
    for row in d2["bindings"]["claims"]:
        if row.get("predicate_id") in {"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR","DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"}:
            row["state"]="PROVED"; row["blocker"]=None
    errs2=evaluate(d2)
    if not any(x.startswith("PREDICATE_NOT_BLOCKED") for x in errs2):
        print(json.dumps({"status":"FAIL","error":"COUNTERFACTUAL_SOURCE_RESTORATION_NOT_DETECTED"})); return 1
    print(json.dumps({"status":"PASS","verified":[
      "EXACT_SIX_BRAIN_BLOBS",
      "BRIDGE_REQUIRES_WHOLE_SOURCE_PROTOCOL_CLOSURE",
      "BOTH_BRIDGE_SOURCE_FAMILIES_REOPENED_BY_LATER_SCOPE_FIREWALL",
      "BOTH_CURRENT_SOURCE_ACCEPTANCE_PREDICATES_BLOCKED_ON_SCOPE_COMPLETENESS",
      "V2_SLICE_TWO_PROOFS_ARE_EXACTLY_THE_AFFECTED_RECEIPTS",
      "QUARANTINE_PRESERVES_RAW_SAMPLE_EVIDENCE_AND_GRANTS_ZERO_CREDIT",
      "COUNTERFACTUAL_SOURCE_RESTORATION_DETECTED"
    ],"effect":"CURRENT_COMPOSITION_ADMISSIBLE_BASELINE_REDUCES_FROM_2_OF_12_TO_0_OF_12_BEFORE_ANY_NEW_INDEPENDENT_RECEIPT"},indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
