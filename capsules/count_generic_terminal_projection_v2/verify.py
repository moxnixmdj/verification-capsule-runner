from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FIX=ROOT/"fixture"

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def blob(path):
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def req(cond,code,errors):
    if not cond: errors.append(code)

def main():
    errors=[]
    expected=load("EXPECTED_BRAIN_BLOBS.json")
    for name,row in expected.items():
        req(blob(name)==row["git_blob_sha"],f"BLOB_MISMATCH:{name}",errors)

    spec=importlib.util.spec_from_file_location("candidate_projection",ROOT/"candidate_runtime.py")
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
    mod.ROOT=FIX

    live=mod.evaluate_live()
    req(live.get("pass") is True,"LIVE_REDUCER_NOT_PASS",errors)
    req(live.get("acceptance_closed_families")==4,"LIVE_FAMILY_CLOSED_NOT_4",errors)
    req(live.get("acceptance_open_families")==15,"LIVE_FAMILY_OPEN_NOT_15",errors)
    req(live.get("atomic_predicates_proved")==11,"LIVE_ATOMIC_PROVED_NOT_11",errors)
    req(live.get("atomic_predicates_unresolved")==27,"LIVE_ATOMIC_OPEN_NOT_27",errors)
    req(set(live.get("baseline_families") or [])=={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"},"BASELINE_DERIVATION",errors)
    req("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY" in set(live.get("accepted_families") or []),"RECOVERY_NOT_DERIVED_ACCEPTED",errors)
    req("SUBAGENT_DELEGATION_AND_COORDINATION" in set(live.get("accepted_families") or []),"DELEGATION_NOT_DERIVED_ACCEPTED",errors)

    docs={k:mod._load(v) for k,v in mod.PATHS.items()}
    shas={v:mod._git_blob_sha(v) for v in mod.PATHS.values()}

    stale=copy.deepcopy(docs)
    stale["authority"]["truth"]["opus55_acceptance"]="3/19_PASS__16/19_OPEN"
    out=mod.evaluate_documents(stale["authority"],stale["closure"],stale["matrix"],stale["atomic_bindings"],
                               stale["predicate_registry"],stale["target_envelope"],shas)
    req(out.get("pass") is False and "AUTHORITY_ACCEPTANCE_MISMATCH" in out.get("errors",[]),"STALE_AUTHORITY_NOT_REJECTED",errors)

    scope=copy.deepcopy(docs)
    row=next(x for x in scope["atomic_bindings"]["claims"] if x["predicate_id"]=="RECOVERY_TERMINAL_NONINFERIOR")
    row["scope_complete"]=False
    scope["atomic_bindings"]["saturation"]["proved_predicate_count"]=10
    scope["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=28
    out=mod.evaluate_documents(scope["authority"],scope["closure"],scope["matrix"],scope["atomic_bindings"],
                               scope["predicate_registry"],scope["target_envelope"],shas)
    req(out.get("pass") is False and "AUTHORITY_ACCEPTANCE_MISMATCH" in out.get("errors",[]),"SCOPE_INCOMPLETE_RECOVERY_NOT_REJECTED",errors)

    future=copy.deepcopy(docs)
    target="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    ids=[p["id"] for p in future["predicate_registry"]["predicates"] if p["family"]==target]
    cmap={x["predicate_id"]:x for x in future["atomic_bindings"]["claims"]}
    for pid in ids:
        if pid in cmap:
            cmap[pid]["state"]="PROVED"; cmap[pid]["scope_complete"]=True
        else:
            future["atomic_bindings"]["claims"].append({"predicate_id":pid,"state":"PROVED","scope_complete":True})
    proved=0
    cmap2={x["predicate_id"]:x for x in future["atomic_bindings"]["claims"]}
    for p in future["predicate_registry"]["predicates"]:
        x=cmap2.get(p["id"],{})
        if x.get("state")=="PROVED" and x.get("scope_complete") is True: proved+=1
    future["atomic_bindings"]["saturation"]["proved_predicate_count"]=proved
    future["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=38-proved
    out=mod.evaluate_documents(future["authority"],future["closure"],future["matrix"],future["atomic_bindings"],
                               future["predicate_registry"],future["target_envelope"],shas)
    req(out.get("pass") is False and "AUTHORITY_ACCEPTANCE_MISMATCH" in out.get("errors",[]),"FUTURE_CLOSURE_NOT_DERIVED",errors)

    source=(ROOT/"candidate_runtime.py").read_text(encoding="utf-8")
    for stale_literal in ("(3,16,19)","(8,30)","DELEGATION_VERIFIED_RESULT_MISSING","EXPECTED_P1_QUARANTINED"):
        req(stale_literal not in source,"STALE_HARDCODE_REMAINS:"+stale_literal,errors)

    result={
      "schema":"PROJECT_BRAIN_COUNT_GENERIC_TERMINAL_PROJECTION_V2_INDEPENDENT_VERIFICATION",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "live_closed_families":4 if not errors else None,
      "live_open_families":15 if not errors else None,
      "live_proved_predicates":11 if not errors else None,
      "live_unresolved_predicates":27 if not errors else None,
      "future_family_closure_requires_no_reducer_code_change":not errors,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
