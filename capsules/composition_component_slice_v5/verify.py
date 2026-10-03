from __future__ import annotations
import hashlib, importlib.util, json
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
    expected_blobs=load("EXPECTED_BRAIN_BLOBS.json")
    for name,row in expected_blobs.items():
        req(blob(name)==row["git_blob_sha"],f"BLOB_MISMATCH:{name}",errors)

    spec=importlib.util.spec_from_file_location("brain_slicer",ROOT/"slicer.py")
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    inp=load("input_v5.json")
    expected=load("expected_v5.json")
    recovery=load("recovery_bridge_verification.json")
    memory=load("memory_bridge_verification.json")
    delegation=load("delegation_bridge_verification.json")
    manifest=load("manifest.json")

    req(inp.get("claim_id")=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1","INPUT_CLAIM",errors)
    req(len(inp.get("interfaces",[]))==12,"INPUT_INTERFACE_COUNT",errors)
    req(inp.get("source_manifest_git_blob_sha")==expected_blobs["manifest.json"]["git_blob_sha"],"INPUT_MANIFEST_BINDING",errors)

    verified_receipts={
      recovery["verified_component_receipt"]["receipt_id"]: recovery["verified_component_receipt"],
      memory["verified_component_receipt"]["receipt_id"]: memory["verified_component_receipt"],
      delegation["verified_component_receipt"]["receipt_id"]: delegation["verified_component_receipt"],
    }
    input_receipts={x["receipt_id"]:x for x in inp.get("receipts",[])}
    req(set(input_receipts)==set(verified_receipts),"RECEIPT_SET_NOT_EXACT_THREE",errors)
    for rid,v in verified_receipts.items():
        row=input_receipts.get(rid) or {}
        for key in ("component_id","interface_id","proved_properties","verified","independent","contamination_clean","acceptance_scoped","binds_frozen_claim","source_family"):
            req(row.get(key)==v.get(key),f"RECEIPT_FIELD_DRIFT:{rid}:{key}",errors)

    req(str(recovery.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"RECOVERY_RECEIPT_NOT_VERIFIED",errors)
    req(str(memory.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"MEMORY_RECEIPT_NOT_VERIFIED",errors)
    req(str(delegation.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"DELEGATION_RECEIPT_NOT_VERIFIED",errors)

    actual=mod.evaluate(inp)
    rows=actual.get("interfaces") or []
    proved=[x for x in rows if x.get("state")=="SCOPED_PROVED"]
    opened=[x for x in rows if x.get("state")=="OPEN"]
    req(len(rows)==12,"ACTUAL_INTERFACE_COUNT",errors)
    req([x.get("component_id") for x in proved]==["memory","recovery","delegation"],"PROVED_COMPONENT_SET_OR_ORDER",errors)
    req(len(proved)==3,"PROVED_COUNT",errors)
    req(len(opened)==9,"OPEN_COUNT",errors)
    req(actual.get("all_used_component_interfaces_scoped_proved") is False,"PARENT_MUST_REMAIN_OPEN",errors)
    req(actual.get("status")=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN","SLICE_STATUS",errors)
    req(actual.get("interfaces")==expected.get("interfaces"),"EXPECTED_PROJECTION_MISMATCH",errors)

    erows={x["component_id"]:x for x in expected.get("interfaces",[])}
    req(erows["recovery"]["supporting_receipt_ids"]==["COMPOSITION_SCOPE_COMPLETE_BRIDGE::SELF_VERIFICATION_DEBUGGING_AND_RECOVERY::recovery::V1"],"RECOVERY_SUPPORT_ID",errors)
    for c in ("browser/computer action","debugging","tool discovery","evidence synthesis","artifact production"):
        req(erows[c]["state"]=="OPEN",f"ADJACENT_COMPONENT_MUST_REMAIN_OPEN:{c}",errors)

    out={
      "schema":"PROJECT_BRAIN_COMPOSITION_COMPONENT_SLICE_V5_INDEPENDENT_VERIFICATION_V1",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "interface_count":12,
      "scoped_proved_count":3 if not errors else None,
      "open_count":9 if not errors else None,
      "scoped_proved_components":["memory","recovery","delegation"] if not errors else [],
      "parent_composition_open":True,
      "strict_opus55_acceptance_delta":0,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
