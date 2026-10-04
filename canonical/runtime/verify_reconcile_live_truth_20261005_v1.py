from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
  "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "fe06033595c4cd6ab71a63531d6a48cb74a3f0fb",
  "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json": "279bd1ce522137fd0df763c712c6bf09803b7a6d",
  "canonical/tests/test_terminal_projection_consistency_v1.py": "aa694f771cdaf3c84221309a72743e37d97af132",
  "canonical/tests/test_brain_witness_normalization_v1.py": "effa53fb345da1609da49b390e8a353cc733bfe1",
  "canonical/tests/test_terminal_next_action_compiler_v1.py": "95719282fb33893c7b08dc763b676b8d50ed6177",
  "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json": "db596861ab2ed25e4772d175cf6e264508c83564",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "c16ba4071525afb12e3d025d056c8bb2bd182019",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
  "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
  "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json": "d37c4e1051429c261717c5091d7a6a5aeff212d8"
}

def blob_sha(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel: str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def norm(x):
    return {
        "witness_id": f"WITNESS::{x.get('predicate_id')}",
        "source_predicate_id": x.get("predicate_id"),
        "proof_kind": x.get("proof_kind"),
        "source_path": x.get("source_path"),
        "source_sha": x.get("source_sha"),
        "independent_or_objective": x.get("independent_or_objective") is True,
        "scope_complete": x.get("scope_complete") is True,
        "objective_ceiling": x.get("objective_ceiling") is True,
        "brain_value": x.get("brain_value"),
        "objective_ceiling_value": x.get("objective_ceiling_value"),
        "basis": x.get("basis"),
        "supporting_sources": x.get("supporting_sources") if isinstance(x.get("supporting_sources"), list) else [],
        "normalized_target_atoms": [],
        "semantic_implications": [],
    }

def main():
    errors=[]
    for rel,sha in EXPECTED.items():
        got=blob_sha(ROOT/rel)
        if got!=sha:
            errors.append(f"BLOB_MISMATCH:{rel}:{got}:{sha}")

    authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
    envelope=load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json")
    witness=load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json")
    hypergraph=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")

    if authority["sources"]["terminal_closure_manifest"]["git_blob_sha"] != EXPECTED["canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"]:
        errors.append("AUTHORITY_CLOSURE_POINTER_STALE")
    if authority["sources"]["acceptance_predicate_evidence_bindings_reconciled"]["git_blob_sha"] != EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]:
        errors.append("AUTHORITY_EVIDENCE_POINTER_STALE")

    proved_claims=[x for x in evidence["claims"] if x.get("state")=="PROVED"]
    expected_witnesses=[norm(x) for x in proved_claims]
    if witness.get("witness_count") != len(expected_witnesses):
        errors.append("WITNESS_COUNT_MISMATCH")
    if witness.get("witnesses") != expected_witnesses:
        errors.append("WITNESS_EXACT_RECOMPUTATION_MISMATCH")
    if witness["authority"]["evidence_bindings"]["git_blob_sha"] != EXPECTED["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]:
        errors.append("WITNESS_SOURCE_POINTER_STALE")
    if witness.get("witness_normalization_verified") is not False:
        errors.append("WITNESS_STALE_VERIFICATION_NOT_REVOKED")
    if witness.get("execution_authority") is not False or witness.get("promotion_authority") is not False:
        errors.append("WITNESS_AUTHORITY_OVERCLAIM")
    if witness.get("capability_credit_delta") != 0 or witness.get("family_credit_delta") != 0:
        errors.append("WITNESS_CREDIT_OVERCLAIM")

    livebench=next(x for x in evidence["claims"] if x.get("predicate_id")=="LIVEBENCH_IF_GE_65_7")
    if livebench.get("state")=="PROVED" or not str(livebench.get("state","")).startswith("QUARANTINED"):
        errors.append("LIVEBENCH_CONTAMINATION_QUARANTINE_LOST")

    families=[x["id"] for x in envelope["families"]]
    residual=set(registry.get("residual_families") or [])
    predicates=registry["predicates"]
    proved={x["predicate_id"] for x in evidence["claims"] if x.get("state")=="PROVED" and x.get("scope_complete") is True}
    byfam={}
    for p in predicates:
        byfam.setdefault(p["family"],[]).append(p["id"])
    accepted={f for f in families if f not in residual}
    for fam,ids in byfam.items():
        if ids and all(i in proved for i in ids):
            accepted.add(fam)
    derived=(len(accepted),len(families)-len(accepted),len(proved),len(predicates)-len(proved))
    if derived != (5,14,12,26):
        errors.append("DERIVED_STATE_NOT_5_19_12_38:"+repr(derived))

    if authority["truth"]["opus55_acceptance"]!="5/19_PASS__14/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_NOT_5_19")
    af=authority["atomic_acceptance_frontier"]
    if (af["proved"],af["unresolved"],af["total"])!=(12,26,38):
        errors.append("AUTHORITY_ATOMIC_NOT_12_26_38")

    actions=[]
    for a in hypergraph["actions"]:
        unresolved=sorted(set(a.get("target_predicates",[]))-proved)
        if not unresolved:
            continue
        unsat=sorted(p["id"] for p in a.get("preconditions",[]) if p.get("satisfied") is False)
        actions.append({
            "id":a["id"],"critical":a.get("critical_path") is True,
            "cost":int(a.get("new_reality_units",0) or 0),"targets":unresolved,
            "available":not unsat,"unsat":unsat
        })
    actions.sort(key=lambda a:(0 if a["critical"] else 1,-len(a["targets"]),a["cost"],a["id"]))
    critical_zero=[a for a in actions if a["critical"] and a["available"] and a["cost"]==0]
    available_zero=[a for a in actions if a["available"] and a["cost"]==0]
    available_any=[a for a in actions if a["available"]]
    primary=(critical_zero or available_zero or available_any)[0]
    blocked_critical=[a for a in actions if a["critical"] and not a["available"]]
    blocked_any=[a for a in actions if not a["available"]]
    blocked=(blocked_critical or blocked_any)[0]
    if primary["id"]!="RAISE_TB4_ATTAINABILITY_UPPER_BOUND_WITHOUT_CASE_EXPOSURE":
        errors.append("PRIMARY_ACTION_CHANGED:"+primary["id"])
    if blocked["id"]!="RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA":
        errors.append("HIGHEST_BLOCKED_CHANGED:"+blocked["id"])
    if set(blocked["unsat"])!={"MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS","MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS"}:
        errors.append("BLOCKED_PRECONDITIONS_CHANGED")

    tp=(ROOT/"canonical/tests/test_terminal_projection_consistency_v1.py").read_text()
    wt=(ROOT/"canonical/tests/test_brain_witness_normalization_v1.py").read_text()
    nt=(ROOT/"canonical/tests/test_terminal_next_action_compiler_v1.py").read_text()
    for name,needle,text in [
        ("projection_4_19",'acceptance_closed_families"],4',tp),
        ("projection_11_38",'atomic_predicates_proved"],11',tp),
        ("witness_9",'witness_count"],9',wt),
        ("next_7",'proved_predicate_count"], 7',nt),
        ("next_31",'unresolved_predicate_count"], 31',nt),
    ]:
        if needle in text:
            errors.append("STALE_TEST_CONSTANT:"+name)

    out={
        "pass":not errors,
        "errors":errors,
        "derived":{"accepted_families":len(accepted),"open_families":len(families)-len(accepted),"proved":len(proved),"unresolved":len(predicates)-len(proved)},
        "witness_count":len(expected_witnesses),
        "livebench_state":livebench.get("state"),
        "primary_action":primary["id"],
        "highest_leverage_blocked":blocked["id"],
        "blocked_preconditions":blocked["unsat"],
        "terminal_goal":False,
        "incremental_spend_usd":0,
        "terminal_cases_consumed":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if not errors else 1)

if __name__=="__main__":
    main()
