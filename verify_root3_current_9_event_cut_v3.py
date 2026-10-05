#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root3_current_9_event_cut_v3"
OUT=ROOT/"root3_current_9_event_cut_v3_receipt.json"

EXPECTED={
 "CANDIDATE.json":"4cb6d1164e0354a50166a7b94a1a56a207d4d336",
 "AUTHORITY.json":"9015b1fcacb40222f920c124986fcea63cc6e5ee",
 "PRIOR_ROOT3.json":"4d8ce78ebe312100bbfc524062199961c0c6479d",
 "RESIDUAL_COMPRESSION.json":"5f3e5b7164f964fb1992b23f35069e3755673271",
 "SUPERPORTFOLIO.json":"e886f262aa4b4946b290d636d336bf857afa946c",
 "UNKNOWN_REDUCTION.json":"ebe8edcda3e0aa7dcffab6032834532a6f06c5f7",
 "UNKNOWN_VERIFICATION.json":"d65875f9abba55d9a58a4f2566f3719bebfb0a04",
 "ROOT2_CURRENT.json":"82612b803c1d47eeb8888cf99a00c14a1bea54e1",
}

def git_blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(name:str):
    p=SUB/name
    got=git_blob(p)
    assert got==EXPECTED[name], (name,got,EXPECTED[name])
    return json.loads(p.read_text(encoding="utf-8"))

def main()->int:
    c=load("CANDIDATE.json")
    a=load("AUTHORITY.json")
    old=load("PRIOR_ROOT3.json")
    residual=load("RESIDUAL_COMPRESSION.json")
    superp=load("SUPERPORTFOLIO.json")
    u=load("UNKNOWN_REDUCTION.json")
    uv=load("UNKNOWN_VERIFICATION.json")
    r2=load("ROOT2_CURRENT.json")

    # Source-address integrity.
    bind=c["source_bindings"]
    assert bind["current_terminal_authority"]["git_blob_sha"]==EXPECTED["AUTHORITY.json"]
    assert bind["prior_root3_minimum_action_cut"]["git_blob_sha"]==EXPECTED["PRIOR_ROOT3.json"]
    assert bind["root3_residual_compression"]["git_blob_sha"]==EXPECTED["RESIDUAL_COMPRESSION.json"]
    assert bind["matched_superportfolio_v2"]["git_blob_sha"]==EXPECTED["SUPERPORTFOLIO.json"]
    assert bind["unknown_domain_acceptance_reduction"]["git_blob_sha"]==EXPECTED["UNKNOWN_REDUCTION.json"]
    assert bind["unknown_domain_independent_verification"]["git_blob_sha"]==EXPECTED["UNKNOWN_VERIFICATION.json"]
    assert bind["root2_current_compilation"]["git_blob_sha"]==EXPECTED["ROOT2_CURRENT.json"]

    # Current authority recomputation.
    root=a["current_root_partition_override"]
    assert root["proved_atomic"]==14 and root["unresolved_atomic"]==24
    assert root["root1_only"]==0 and root["root2_only"]==15
    assert root["root3_only"]==6 and root["root2_and_root3"]==3
    assert root["root2_touching"]==18
    assert root["unknown_domain_class"].startswith("CLOSED__PROVED")
    root3_touching=root["root3_only"]+root["root2_and_root3"]
    assert root3_touching==9
    assert a["next_terminal_action"].startswith("SOLVE_MINIMUM_ZERO_REALITY_CERTIFICATE_CUT_OVER_ACTIVE_ROOT2_18__RECOMPUTE_ROOT3_9_TOUCHING_EVENT_SET")

    # Independent Unknown-Domain promotion is load-bearing for deletion.
    assert u["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    assert u["deduction"]["new_predicate_state"]=="PROVED"
    assert u["deduction"]["scope_complete"] is True
    assert u["deduction"]["independent_or_objective"] is True
    assert u["current_authority"] is True
    assert uv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

    # Old Root3 cut and exact stale residual.
    assert old["derivation"]["live_root3_predicates"]==10
    assert old["derivation"]["formal_matched_scope_targets"]==7
    assert old["derivation"]["direct_oracle_residual"]=="4_FROZEN_LEAVES_ACROSS_2_PREDICATES"
    old_events={x["id"] for x in old["minimum_event_classes"]}
    expected_events={"NEW_SCOPE_CERTIFICATE_EVENT","UPSTREAM_SCOPE_RECEIPT_EVENT","ROOT3_FRESH_REALITY_EVENT"}
    assert old_events==expected_events

    rows={x["predicate_id"]:x for x in residual["compressed_residuals"]}
    assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" in rows
    assert "FINANCE_UNCOVERED_SCOPE_AUDIT" in rows
    assert "COMPOSITION_COMPONENT_SCOPED_PROOFS" in rows
    unknown_leaves=rows["UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]["frozen_direct_leaf_ids"]
    assert len(unknown_leaves)==2
    assert rows["FINANCE_UNCOVERED_SCOPE_AUDIT"]["current_residual"]=="TWO_FROZEN_DIRECT_ORACLE_LEAVES"

    # Seven shared matched-scope targets are unchanged.
    matched=[x["predicate_id"] for x in superp["matched_scope_targets"]]
    assert len(matched)==7 and len(set(matched))==7
    assert superp["execution_compression"]["root3_matched_scope_target_count"]==7
    assert superp["execution_compression"]["shared_future_superportfolio_wave_count"]==1
    assert superp["fallback"]["direct_oracle_batch"]["predicate_count"]==2

    # Current exact nine-predicate partition.
    cp=c["derivation"]["current_predicate_partition"]
    assert cp["matched_scope_targets"]==matched
    assert cp["event_driven_dependency"]==["COMPOSITION_COMPONENT_SCOPED_PROOFS"]
    assert cp["direct_oracle_residual"]==["FINANCE_UNCOVERED_SCOPE_AUDIT"]
    current_set=set(matched)|{"COMPOSITION_COMPONENT_SCOPED_PROOFS","FINANCE_UNCOVERED_SCOPE_AUDIT"}
    assert len(current_set)==9
    assert c["derivation"]["current_root3_touching"]==root3_touching==9
    assert c["derivation"]["current_global_state"]["root3_touching"]==9

    # Root2 remained exact-18; Unknown Domain closure was Root3-only.
    assert r2["exact_state"]["root3_only"]==6
    assert r2["exact_state"]["root2_and_root3"]==3
    assert r2["exact_state"]["root2_touching"]==18
    assert r2["derivation"]["post_unknown_domain_rule"].startswith("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT_WAS_ROOT3_ONLY")

    # Delete exactly the now-proved Unknown-Domain direct leaves, nothing else.
    assert c["stale_work_deleted"]["predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    assert c["stale_work_deleted"]["prior_direct_oracle_leaves"]==unknown_leaves
    shape=c["minimum_future_reality_shape_if_no_stronger_proof_arrives"]
    assert shape["matched_superportfolio_wave_count"]==1
    assert shape["matched_superportfolio_target_count"]==7
    assert shape["direct_oracle_predicate_count"]==1
    assert shape["direct_oracle_predicate"]=="FINANCE_UNCOVERED_SCOPE_AUDIT"
    assert shape["direct_oracle_leaf_count"]==2
    assert shape["unknown_domain_direct_oracle_leaf_count"]==0
    assert shape["deleted_direct_oracle_predicates"]==1
    assert shape["deleted_direct_oracle_leaves"]==2

    # Event topology is unchanged and no execution/credit sneaks in.
    assert {x["id"] for x in c["minimum_event_classes"]}==expected_events
    for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"):
        assert c[k] is False
    for v in c["accounting"].values():
        assert v==0

    receipt={
      "schema":"PROJECT_BRAIN_ROOT3_CURRENT_14_24_MINIMUM_EVENT_CUT_V3_INDEPENDENT_VERIFICATION",
      "status":"PASS__CURRENT_ROOT3_EXACTLY_9_TOUCHING__UNKNOWN_DOMAIN_DIRECT_ORACLE_DELETED__THREE_EVENT_CLASSES_PRESERVED__ZERO_CREDIT",
      "subject_blobs":EXPECTED,
      "verified":{
        "current_root3_touching":9,
        "matched_scope_targets":7,
        "event_driven_dependency_predicates":1,
        "surviving_direct_oracle_predicates":1,
        "surviving_direct_oracle_leaves":2,
        "deleted_unknown_domain_direct_oracle_leaves":2,
        "root2_touching_unchanged":18,
        "event_classes":sorted(expected_events),
      },
      "authority":{"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,
                    "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
