from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

RECOVERY_ROOT=ROOT/"capsules/composition_recovery_bridge_v1"
V6_ROOT=ROOT/"capsules/composition_slice_v6"

EXPECTED={
    HERE/"CANDIDATE.json":"c0124a76c362007293e54927e8bee69eb0bc913c",
    RECOVERY_ROOT/"envelope.json":"661a57f839101fbf54c7e4edc76166c65ce9327d",
    RECOVERY_ROOT/"protocols.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
    RECOVERY_ROOT/"manifest.json":"9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    RECOVERY_ROOT/"recovery_scope.json":"981c8ac9b66ee7fccf5b531525849e29df9be483",
    RECOVERY_ROOT/"recovery_acceptance.json":"48a865f38f65be212df1cf0ba52d296b71cd003a",
    V6_ROOT/"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json":"5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
}
RECOVERY_PREDS={
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}
DEBUG_DIMENSIONS={
    "semantic self-check",
    "counterexample discovery",
    "earliest causal failure localization",
    "repair selection",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def req(cond,code,errors):
    if not cond:
        errors.append(code)

def main():
    errors=[]
    for p,e in EXPECTED.items():
        req(p.exists(),f"MISSING:{p}",errors)
        if p.exists():
            req(blob(p)==e,f"BLOB_MISMATCH:{p.name}",errors)

    c=load(HERE/"CANDIDATE.json")
    env=load(RECOVERY_ROOT/"envelope.json")
    protocols=load(RECOVERY_ROOT/"protocols.json")
    manifest=load(RECOVERY_ROOT/"manifest.json")
    scope=load(RECOVERY_ROOT/"recovery_scope.json")
    acc=load(RECOVERY_ROOT/"recovery_acceptance.json")
    auth=load(V6_ROOT/"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")

    req(c.get("schema")=="PROJECT_BRAIN_COMPOSITION_DEBUGGING_SCOPE_COMPLETE_BRIDGE_V1","CANDIDATE_SCHEMA",errors)
    req(c.get("claim_id")=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1","CLAIM_ID",errors)
    cb=c.get("component_binding") or {}
    req(cb.get("component_id")=="debugging","COMPONENT_ID",errors)
    req(cb.get("interface_id")=="coding+debugging+tool discovery","INTERFACE_ID",errors)
    req(cb.get("proved_properties_after_independent_verification")==["SCOPED_ACCEPTANCE_PROOF"],"PROVED_PROPERTY",errors)

    rows=[x for x in manifest.get("interfaces",[]) if isinstance(x,dict) and x.get("component_id")=="debugging"]
    req(len(rows)==1,"FROZEN_DEBUGGING_COMPONENT_NOT_UNIQUE",errors)
    if rows:
        req(rows[0].get("interface_id")=="coding+debugging+tool discovery","FROZEN_DEBUGGING_INTERFACE_DRIFT",errors)
        req(rows[0].get("required_properties")==["SCOPED_ACCEPTANCE_PROOF"],"FROZEN_DEBUGGING_PROPERTY_DRIFT",errors)

    src=next((x for x in protocols.get("protocols",[]) if x.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"),None)
    dst=next((x for x in protocols.get("protocols",[]) if x.get("family")=="MULTI_CAPABILITY_COMPOSITION"),None)
    req(isinstance(src,dict),"RECOVERY_PROTOCOL_MISSING",errors)
    req(isinstance(dst,dict),"COMPOSITION_PROTOCOL_MISSING",errors)
    if src:
        dims=set(src.get("task_dimensions") or [])
        req(DEBUG_DIMENSIONS.issubset(dims),"DEBUGGING_DIMENSIONS_NOT_COVERED",errors)
        req("terminal_recovery_rate" in (src.get("primary_metrics") or []),"RECOVERY_METRIC_MISSING",errors)
        req("true_root_cause_topk" in (src.get("primary_metrics") or []),"ROOT_CAUSE_METRIC_MISSING",errors)
    if dst:
        req("coding+debugging+tool discovery" in (dst.get("task_dimensions") or []),"COMPOSITION_DEBUGGING_INTERFACE_MISSING",errors)

    env_rows=env.get("families",[]) if isinstance(env,dict) else []
    em={x.get("id"):x.get("useful_behavior") for x in env_rows if isinstance(x,dict)}
    src_behavior=str(em.get("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",""))
    req("diagnose failures" in src_behavior.lower(),"SOURCE_ENVELOPE_LACKS_DEBUGGING",errors)
    req("falsify conclusions" in src_behavior.lower(),"SOURCE_ENVELOPE_LACKS_FALSIFICATION",errors)

    req(str(scope.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SOURCE_SCOPE_NOT_INDEPENDENT_PASS",errors)
    sv=scope.get("verified") or {}
    req(sv.get("scope_complete") is True,"SOURCE_SCOPE_NOT_COMPLETE",errors)
    req(sv.get("objective_ceiling_or_floor") is True,"SOURCE_BOUND_NOT_OBJECTIVE",errors)
    req(set(sv.get("predicates") or [])==RECOVERY_PREDS,"SOURCE_SCOPE_PREDICATES_DRIFT",errors)
    ub=sv.get("universal_achieved_bounds") or {}
    req(ub.get("causal_localization")==1,"CAUSAL_LOCALIZATION_NOT_CEILING",errors)
    req(ub.get("terminal_recovery")==1,"TERMINAL_RECOVERY_NOT_CEILING",errors)
    req(ub.get("critical_fail_closed_misses")==0,"FAIL_CLOSED_NOT_FLOOR",errors)

    req(str(acc.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SOURCE_ACCEPTANCE_NOT_INDEPENDENT_PASS",errors)
    vr=acc.get("verified_result") or {}
    req(vr.get("newly_closed_families")==["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"],"SOURCE_FAMILY_NOT_CLOSED",errors)
    req(set(vr.get("newly_proved_predicates") or [])==RECOVERY_PREDS,"SOURCE_ACCEPTANCE_PREDICATES_DRIFT",errors)

    truth=auth.get("truth") or {}
    req(truth.get("current_admissible_scoped_proved")==4,"V6_PROVED_COUNT_DRIFT",errors)
    req(truth.get("current_open")==8,"V6_OPEN_COUNT_DRIFT",errors)
    req("debugging" in (auth.get("open_components") or []),"DEBUGGING_NOT_CURRENTLY_OPEN",errors)
    req("debugging" not in (truth.get("current_scoped_proved_components") or []),"DEBUGGING_ALREADY_PROVED",errors)

    d=c.get("derivation") or {}
    req(set(d.get("source_protocol_debugging_dimensions") or [])==DEBUG_DIMENSIONS,"CANDIDATE_DEBUG_DIMENSIONS_DRIFT",errors)
    req(d.get("relation")=="SOURCE_SCOPE_IS_EXACT_OR_STRONGER_FOR_LITERAL_DEBUGGING_COMPONENT","RELATION_NOT_EXACT_OR_STRONGER",errors)
    req(d.get("source_scope_complete") is True and d.get("source_acceptance_closed") is True,"CANDIDATE_SOURCE_CLOSURE_FALSE",errors)

    receipt=c.get("candidate_receipt") or {}
    req(receipt.get("component_id")=="debugging","RECEIPT_COMPONENT",errors)
    req(receipt.get("interface_id")=="coding+debugging+tool discovery","RECEIPT_INTERFACE",errors)
    req(receipt.get("proved_properties")==["SCOPED_ACCEPTANCE_PROOF"],"RECEIPT_PROPERTY",errors)
    req(receipt.get("verified") is False and receipt.get("independent") is False,"CANDIDATE_SELF_PROMOTION",errors)
    req(receipt.get("contamination_clean") is True and receipt.get("acceptance_scoped") is True,"RECEIPT_SCOPE_OR_CONTAMINATION",errors)

    excluded=set((c.get("scope_guard") or {}).get("excluded_scope") or [])
    req({"CODING_COMPONENT","TOOL_DISCOVERY_COMPONENT","RECOVERY_COMPONENT_CREDIT_FROM_THIS_RECEIPT","GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS","CROSS_CAPABILITY_STATE_HANDOFF_AND_ROLLBACK"}.issubset(excluded),"ADJACENT_SCOPE_NOT_EXCLUDED",errors)
    req(c.get("execution_authority") is False and c.get("promotion_authority") is False and c.get("fresh_reality_authority") is False,"AUTHORITY_ESCALATION",errors)
    req(c.get("acceptance_credit_delta")==0 and c.get("family_credit_delta")==0 and c.get("ownership_credit_delta")==0,"FORBIDDEN_PARENT_CREDIT",errors)

    out={
      "schema":"PROJECT_BRAIN_COMPOSITION_DEBUGGING_BRIDGE_INDEPENDENT_VERIFICATION_V1",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "verified_component":"debugging" if not errors else None,
      "verified_interface":"coding+debugging+tool discovery" if not errors else None,
      "source_family":"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY" if not errors else None,
      "source_scope_exact_or_stronger_for_component":not errors,
      "proved_properties":["SCOPED_ACCEPTANCE_PROOF"] if not errors else [],
      "projected_composition_scoped_proved":5 if not errors else 4,
      "projected_composition_open":7 if not errors else 8,
      "adjacent_component_credit":False,
      "parent_composition_credit":False,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "ownership_credit_delta":0,
      "fresh_reality_authority":False,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
