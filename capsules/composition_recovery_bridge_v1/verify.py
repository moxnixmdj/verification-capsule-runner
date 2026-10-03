from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RECOVERY_PREDS={
 "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
 "RECOVERY_TERMINAL_NONINFERIOR",
 "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def blob(name):
    b=(ROOT/name).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def req(cond,code,errors):
    if not cond:
        errors.append(code)

def main():
    errors=[]
    expected=load("EXPECTED_BRAIN_BLOBS.json")
    for name,row in expected.items():
        req(blob(name)==row["git_blob_sha"],f"BLOB_MISMATCH:{name}",errors)

    bridge=load("bridge.json")
    env=load("envelope.json")
    protocols=load("protocols.json")
    manifest=load("manifest.json")
    scope=load("recovery_scope.json")
    acc=load("recovery_acceptance.json")
    evidence=load("evidence_bindings.json")

    req(bridge.get("schema")=="PROJECT_BRAIN_COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_V1","BRIDGE_SCHEMA",errors)
    req(bridge.get("claim_id")=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1","CLAIM_ID",errors)
    cb=bridge.get("component_binding") or {}
    req(cb.get("component_id")=="recovery","COMPONENT_ID",errors)
    req(cb.get("interface_id")=="browser/computer action+memory+recovery","INTERFACE_ID",errors)
    req(cb.get("proved_properties_after_independent_verification")==["SCOPED_ACCEPTANCE_PROOF"],"PROVED_PROPERTY",errors)

    rows=[x for x in manifest.get("interfaces",[]) if isinstance(x,dict) and x.get("component_id")=="recovery"]
    req(len(rows)==1,"FROZEN_RECOVERY_COMPONENT_NOT_UNIQUE",errors)
    if rows:
        req(rows[0].get("interface_id")=="browser/computer action+memory+recovery","FROZEN_INTERFACE_DRIFT",errors)
        req(rows[0].get("required_properties")==["SCOPED_ACCEPTANCE_PROOF"],"FROZEN_PROPERTY_DRIFT",errors)

    src=next((x for x in protocols.get("protocols",[]) if x.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"),None)
    dst=next((x for x in protocols.get("protocols",[]) if x.get("family")=="MULTI_CAPABILITY_COMPOSITION"),None)
    req(isinstance(src,dict),"RECOVERY_PROTOCOL_MISSING",errors)
    req(isinstance(dst,dict),"COMPOSITION_PROTOCOL_MISSING",errors)
    if src:
        req("recovery after injected failure" in src.get("task_dimensions",[]),"RECOVERY_DIMENSION_MISSING",errors)
        req("terminal_recovery_rate" in src.get("primary_metrics",[]),"TERMINAL_RECOVERY_METRIC_MISSING",errors)
    if dst:
        req("browser/computer action+memory+recovery" in dst.get("task_dimensions",[]),"COMPOSITION_RECOVERY_INTERFACE_MISSING",errors)

    env_rows=env.get("families",[]) if isinstance(env,dict) else (env if isinstance(env,list) else [])
    em={x.get("id"):x.get("useful_behavior") for x in env_rows if isinstance(x,dict)}
    req("recover" in str(em.get("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","")).lower(),"RECOVERY_ENVELOPE_SEMANTICS",errors)
    req("Compose reasoning, research, tools, code, memory, actions and verification into one causal execution system."==em.get("MULTI_CAPABILITY_COMPOSITION"),"COMPOSITION_ENVELOPE_DRIFT",errors)

    req(str(scope.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SCOPE_NOT_INDEPENDENT_PASS",errors)
    sv=scope.get("verified") or {}
    req(sv.get("scope_complete") is True,"SCOPE_NOT_COMPLETE",errors)
    req(sv.get("objective_ceiling_or_floor") is True,"OBJECTIVE_BOUND_NOT_COMPLETE",errors)
    req(set(sv.get("predicates") or [])==RECOVERY_PREDS,"SCOPE_PREDICATES_DRIFT",errors)
    ub=sv.get("universal_achieved_bounds") or {}
    req(ub.get("terminal_recovery")==1,"TERMINAL_RECOVERY_NOT_CEILING",errors)
    req(ub.get("critical_fail_closed_misses")==0,"FAIL_CLOSED_NOT_FLOOR",errors)

    req(str(acc.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"ACCEPTANCE_NOT_INDEPENDENT_PASS",errors)
    vr=acc.get("verified_result") or {}
    req(vr.get("newly_closed_families")==["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"],"ACCEPTANCE_FAMILY_DRIFT",errors)
    req(set(vr.get("newly_proved_predicates") or [])==RECOVERY_PREDS,"ACCEPTANCE_PREDICATES_DRIFT",errors)
    req(vr.get("recovery_only_delta") is True,"ACCEPTANCE_NOT_RECOVERY_ONLY",errors)

    erows={x.get("predicate_id"):x for x in evidence.get("claims",[]) if isinstance(x,dict) and x.get("predicate_id") in RECOVERY_PREDS}
    req(set(erows)==RECOVERY_PREDS,"CURRENT_LEDGER_RECOVERY_SET",errors)
    for pid,row in erows.items():
        req(row.get("state")=="PROVED",f"LEDGER_NOT_PROVED:{pid}",errors)
        req(row.get("scope_complete") is True,f"LEDGER_SCOPE_NOT_COMPLETE:{pid}",errors)
        req(row.get("source_path")=="canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",f"LEDGER_SOURCE_DRIFT:{pid}",errors)

    receipt=bridge.get("candidate_receipt") or {}
    req(receipt.get("verified") is False,"CANDIDATE_SELF_VERIFIED",errors)
    req(receipt.get("independent") is False,"CANDIDATE_SELF_INDEPENDENT",errors)
    req(receipt.get("acceptance_scoped") is True,"RECEIPT_NOT_ACCEPTANCE_SCOPED",errors)
    req(receipt.get("contamination_clean") is True,"RECEIPT_NOT_CONTAMINATION_CLEAN",errors)
    req(receipt.get("binds_frozen_claim")=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1","RECEIPT_CLAIM_DRIFT",errors)
    req(bridge.get("execution_authority") is False,"EXECUTION_AUTHORITY_FORBIDDEN",errors)
    req(bridge.get("promotion_authority") is False,"PROMOTION_AUTHORITY_FORBIDDEN",errors)
    excluded=set((bridge.get("scope_guard") or {}).get("excluded_scope") or [])
    req({"BROWSER_COMPUTER_ACTION_COMPONENT","MEMORY_COMPONENT","GENERAL_DEBUGGING_COMPONENT","GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS"}.issubset(excluded),"ADJACENT_SCOPE_NOT_EXCLUDED",errors)

    out={
      "schema":"PROJECT_BRAIN_COMPOSITION_RECOVERY_BRIDGE_INDEPENDENT_VERIFICATION_V1",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "verified_component":"recovery" if not errors else None,
      "verified_interface":"browser/computer action+memory+recovery" if not errors else None,
      "proved_properties":["SCOPED_ACCEPTANCE_PROOF"] if not errors else [],
      "adjacent_component_credit":False,
      "parent_composition_credit":False,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
