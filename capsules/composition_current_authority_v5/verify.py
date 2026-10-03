from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def blob(name):
    b=(ROOT/name).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def req(cond,code,errors):
    if not cond: errors.append(code)

def main():
    errors=[]
    expected=load("EXPECTED_BRAIN_BLOBS.json")
    for name,row in expected.items():
        req(blob(name)==row["git_blob_sha"],f"BLOB_MISMATCH:{name}",errors)

    a=load("current_authority_v5.json")
    t=load("terminal_authority.json")
    s=load("slice_verification_v5.json")

    req(a.get("schema")=="PROJECT_BRAIN_COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5","AUTHORITY_SCHEMA",errors)
    truth=a.get("truth") or {}
    req(truth.get("frozen_interface_count")==12,"FROZEN_COUNT",errors)
    req(truth.get("current_admissible_scoped_proved")==3,"PROVED_COUNT",errors)
    req(truth.get("current_open")==9,"OPEN_COUNT",errors)
    req(truth.get("current_scoped_proved_components")==["memory","recovery","delegation"],"PROVED_COMPONENTS",errors)
    req(truth.get("parent_composition_predicate_closed") is False,"PARENT_MUST_REMAIN_OPEN",errors)
    req(truth.get("strict_opus55_acceptance_delta")==0,"AUTHORITY_ACCEPTANCE_DELTA",errors)
    req(a.get("execution_authority") is False,"EXECUTION_AUTHORITY_FORBIDDEN",errors)
    req(a.get("promotion_authority") is False,"PROMOTION_AUTHORITY_FORBIDDEN",errors)

    req(str(s.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SLICE_NOT_INDEPENDENT_PASS",errors)
    sv=s.get("verified") or {}
    req(sv.get("interface_count")==12,"SLICE_INTERFACE_COUNT",errors)
    req(sv.get("scoped_proved_count")==3,"SLICE_PROVED_COUNT",errors)
    req(sv.get("open_count")==9,"SLICE_OPEN_COUNT",errors)
    req(sv.get("scoped_proved_components")==["memory","recovery","delegation"],"SLICE_COMPONENTS",errors)
    req(sv.get("parent_composition_open") is True,"SLICE_PARENT_NOT_OPEN",errors)
    req((a.get("current_slice") or {}).get("verification_git_blob_sha")==expected["slice_verification_v5.json"]["git_blob_sha"],"SLICE_SHA_BINDING",errors)

    req(t.get("truth",{}).get("opus55_acceptance")=="4/19_PASS__15/19_OPEN","STRICT_ACCEPTANCE_DRIFT",errors)
    req(t.get("truth",{}).get("achieved") is False,"TERMINAL_FALSE_REQUIRED",errors)
    comp=(t.get("integrator_reconciliation_20261002_current") or {}).get("composition")
    req(comp=="3_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_AND_DELEGATION_SCOPED_PROVED__9_OPEN__PARENT_OPEN","TERMINAL_COMPOSITION_PROJECTION",errors)
    residual=set(t.get("residual") or [])
    req("FROZEN_COMPOSITION_COMPONENT_INTERFACES__3_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_AND_DELEGATION_CURRENT_SOURCE_SCOPED_PROVED__9_OPEN__PARENT_OPEN__ZERO_CREDIT" in residual,"RESIDUAL_3_OF_12_MISSING",errors)
    req("COMPOSITION_CURRENT_SLICE_V5_RECEIPT_DERIVED__MEMORY_RECOVERY_AND_DELEGATION_SCOPED_PROVED__9_COMPONENT_INTERFACES_OPEN__HISTORICAL_QUARANTINED_RECEIPTS_NOT_REUSED__PARENT_OPEN" in residual,"RESIDUAL_V5_MISSING",errors)
    req("FROZEN_COMPOSITION_COMPONENT_INTERFACES__2_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_AND_DELEGATION_CURRENT_SOURCE_SCOPED_PROVED__10_OPEN__PARENT_OPEN__ZERO_CREDIT" not in residual,"STALE_LIVE_2_OF_12_REMAINS",errors)

    sources=t.get("sources") or {}
    req("composition_component_proof_current_authority_v5" in sources,"V5_AUTHORITY_POINTER_MISSING",errors)
    req("composition_component_proof_current_slice_v5" in sources,"V5_SLICE_POINTER_MISSING",errors)
    req("composition_recovery_scope_complete_bridge" in sources,"RECOVERY_BRIDGE_POINTER_MISSING",errors)

    out={
      "schema":"PROJECT_BRAIN_COMPOSITION_CURRENT_AUTHORITY_V5_INDEPENDENT_VERIFICATION_V1",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "verified_component_state":"3_OF_12__MEMORY_RECOVERY_DELEGATION__9_OPEN" if not errors else None,
      "strict_opus55_acceptance":"4_OF_19__11_OF_38_UNCHANGED" if not errors else None,
      "parent_composition_open":True,
      "terminal_goal_achieved":False,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
