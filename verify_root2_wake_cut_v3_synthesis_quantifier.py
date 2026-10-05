#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_wake_cut_v3_synthesis_quantifier"
OUT=ROOT/"root2_wake_cut_v3_synthesis_quantifier_receipt.json"

FILES={
 "v3":(SUB/"ROOT2_18_WAKE_AWARE_ZERO_REALITY_CUT_V3.json","e211ac443721cb4b36bf51a99efbfe31a30d681b"),
 "v2":(SUB/"ROOT2_18_WAKE_AWARE_ZERO_REALITY_CUT_V2.json","d9e7965346fad08855b13fd049da3f657a1b98df"),
 "quarantine":(SUB/"SYNTHESIS_SCOPE_CERTIFICATE_REUSE_OVEREXTENSION_QUARANTINE_ACTIVATION_20261005_V1.json","30d509bb0edc7a3bd7cf74feddd7bafbcce73d19"),
 "scope6":(SUB/"SIX_BENCHMARK_PROXY_SCOPE_REPAIR_FRONTIER_V3_ACTIVATION_V1.json","2cdcb6eb87a9303cd407998264450e6e8552cd61"),
 "root2v4":(SUB/"ROOT2_18_CURRENT_14_24_CURSOR_ROUTE_V4_ACTIVATION_V1.json","d739ade25b0c00cee069add72dab9677fa31e027"),
}
OLD_BREAK="DELETE_REDUNDANT_SYNTHESIS_SCOPE_CONSTRUCTION_BECAUSE_EXACT_SCOPE_CERTIFICATE_IS_ALREADY_CLOSED"
NEW_BREAK="DELETE_ONLY_SYNTHESIS_ACCEPTANCE_PREDICATE_SCOPE_RECONSTRUCTION__PRESERVE_ONE_SHARED_SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_ROOT_FOR_FAMILY_SCOPE_REPAIR"
OLD_RULE="NO_REOPEN_SYNTHESIS_SCOPE_CONSTRUCTION"
NEW_RULES={
 "NO_REOPEN_SYNTHESIS_ACCEPTANCE_PREDICATE_SCOPE_CONSTRUCTION",
 "DO_NOT_SUPPRESS_SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS_ROOT_IN_SCOPE_REPAIR_SCHEDULER",
 "TARGET_ACCEPTANCE_SCOPE_SUBSET_OR_SUPERSET_RELATION_IS_NOT_WHOLE_BEHAVIOR_INPUT_DOMAIN_TOTALITY",
 "ONE_SHARED_SYNTHESIS_TYPED_INPUT_SCOPE_ROOT_ONLY__NO_PER_FAMILY_DUPLICATION",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name):
    p,expected=FILES[name]
    got=blob(p)
    assert got==expected,(name,got,expected)
    return json.loads(p.read_text(encoding="utf-8"))

def groups(x):
    return {g["id"]:g for g in x["active_non_owner_zero_reality_groups"]}

def main()->int:
    v3,v2,q,s6,r2v4=(load(x) for x in ("v3","v2","quarantine","scope6","root2v4"))

    # The baseline Root2 scheduler is already an exact current-18 scheduling authority.
    assert r2v4["status"].startswith("ACTIVE__EXACT_18_ROOT2_SCHEDULING")
    assert r2v4["authority"]=={"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}

    # The later verified scope repair explicitly rejects whole-leaf totality.
    assert q["status"].startswith("ACTIVE__SYNTHESIS_WHOLE_LEAF_SCOPE_OVEREXTENSION_QUARANTINED")
    assert q["restored_root"]["id"]=="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"
    assert q["restored_root"]["multiplicity"]==1
    assert q["restored_root"]["fanout"]==[
      "PROFESSIONAL_KNOWLEDGE_WORK",
      "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
      "AGENTIC_SCIENTIFIC_RESEARCH",
    ]
    assert "SYNTHESIS_SCOPE_CERTIFICATE_V1_PREDICATE_LEVEL_ROOT3_RELATION" in q["effects"]["preserve"]
    assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR_ROOT2_PERFORMANCE_OBLIGATION" in q["effects"]["preserve"]
    assert q["effects"]["activate"]==["SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"]
    assert "TARGET_SCOPE_SUBSET_OF_WITNESS_SCOPE_IS_NOT_WITNESS_INPUT_DOMAIN_TOTALITY" in q["hard_rules"]
    assert q["scheduling_authority"] is True
    assert q["execution_authority"] is False and q["promotion_authority"] is False and q["fresh_reality_authority"] is False

    assert s6["status"].startswith("ACTIVE__FAIL_CLOSED_TRUTH_REPAIR")
    assert "REOPEN_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001_WHOLE_LEAF_SCOPE_AS_ONE_SHARED_TYPED_INPUT_DOMAIN_ROOT" in s6["effects"]
    assert "PRESERVE_VALID_SYNTHESIS_ACCEPTANCE_PREDICATE_SCOPE_CERTIFICATE" in s6["effects"]
    assert "DO_NOT_DUPLICATE_SYNTHESIS_SCOPE_WORK_ACROSS_THREE_FAMILIES" in s6["effects"]

    # V3 must preserve every Root2 partition/scheduling fact except the synthesis quantifier wording.
    for key in ("exact_state","event_driven_owner_receipt_lane","deferred_fresh_reality_lane","partition","accounting"):
        assert v3[key]==v2[key],("UNEXPECTED_GLOBAL_DELTA",key)
    assert v3["exact_state"]["root2_touching"]==18
    assert v3["partition"]["counts"]=={"active_non_owner_zero_reality":15,"event_only_atomic":2,"fresh_reality_deferred":1,"total":18}

    g2,g3=groups(v2),groups(v3)
    assert set(g2)==set(g3)
    for gid in sorted(g2):
        if gid!="R2F_FINANCE_AND_SYNTHESIS_CERTIFICATE_COMPILATION":
            assert g3[gid]==g2[gid],("NON_SYNTHESIS_GROUP_DRIFT",gid)

    old=g2["R2F_FINANCE_AND_SYNTHESIS_CERTIFICATE_COMPILATION"]
    new=g3["R2F_FINANCE_AND_SYNTHESIS_CERTIFICATE_COMPILATION"]
    assert old["predicates"]==new["predicates"]==["FINANCE_ACCOUNTING_INDEX_GE_61","SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
    assert old["closure_claim"] is False and new["closure_claim"] is False
    assert old["synthesis_scope_construction_deleted"] is True
    assert "synthesis_scope_construction_deleted" not in new
    assert new["synthesis_acceptance_predicate_scope_reconstruction_deleted"] is True
    assert new["synthesis_whole_leaf_typed_input_scope_root_preserved"] is True
    assert new["synthesis_scope_repair_root_id"]=="SYNTHESIS_TYPED_INPUT_DOMAIN_SCOPE_COMPLETENESS"
    assert new["synthesis_scope_repair_fanout"]==q["restored_root"]["fanout"]
    assert "DO_NOT_INFER_WHOLE_BEHAVIOR_INPUT_DOMAIN_TOTALITY" in new["action"]
    assert "SEPARATE_SHARED_SCOPE_REPAIR_ROOT" in new["action"]

    b2,b3=v2["scheduler_breakthroughs"],v3["scheduler_breakthroughs"]
    assert OLD_BREAK in b2 and OLD_BREAK not in b3
    assert NEW_BREAK not in b2 and NEW_BREAK in b3
    assert sorted(x for x in b2 if x!=OLD_BREAK)==sorted(x for x in b3 if x!=NEW_BREAK)

    h2,h3=set(v2["hard_rules"]),set(v3["hard_rules"])
    assert OLD_RULE in h2 and OLD_RULE not in h3
    assert h3==(h2-{OLD_RULE})|NEW_RULES

    # All old authority bindings remain unchanged; only the new truth-repair bindings are additive.
    for k,val in v2["authorities"].items():
        assert v3["authorities"][k]==val,("AUTHORITY_DRIFT",k)
    assert v3["authorities"]["synthesis_scope_overextension_quarantine_activation"]["git_blob_sha"]==FILES["quarantine"][1]
    assert v3["authorities"]["six_scope_frontier_v3_activation"]["git_blob_sha"]==FILES["scope6"][1]
    assert v3["authorities"]["root2_v4_activation"]["git_blob_sha"]==FILES["root2v4"][1]

    tr=v3["concurrency_truth_repair"]
    assert tr["invalid_inference"]=="VERIFIED_PREDICATE_LEVEL_SYNTHESIS_SCOPE_CERTIFICATE=>WHOLE_EVIDENCE_TO_AUDIENCE_SYNTHESIS_001_INPUT_DOMAIN_TOTALITY"
    assert tr["scheduling_consequence"]=="ROOT2_MUST_NOT_DUPLICATE_PREDICATE_SCOPE_WORK__SCOPE_REPAIR_SCHEDULER_MUST_NOT_DELETE_THE_SHARED_WHOLE_LEAF_TYPED_INPUT_ROOT"
    assert tr["acceptance_credit_delta"]==0

    # Candidate is fail-closed; this proof grants merge/activation eligibility, not execution or fresh reality.
    assert v3["scheduling_authority"] is False
    assert v3["execution_authority"] is False
    assert v3["promotion_authority"] is False
    assert v3["fresh_reality_authority"] is False
    assert v3["independent_verification_required"] is True
    assert all(x==0 for x in v3["accounting"].values())

    receipt={
      "schema":"PROJECT_BRAIN_ROOT2_WAKE_CUT_V3_SYNTHESIS_QUANTIFIER_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__ONLY_SYNTHESIS_QUANTIFIER_BOUNDARY_REPAIRED__EXACT_ROOT2_18_PARTITION_PRESERVED__WHOLE_LEAF_SCOPE_ROOT_PRESERVED__ZERO_CREDIT",
      "verified":{
        "root2_touching":18,
        "active_non_owner_zero_reality":15,
        "event_only_atomic":2,
        "fresh_reality_deferred":1,
        "non_synthesis_group_mutations":0,
        "synthesis_acceptance_predicate_scope_reconstruction_deleted":True,
        "synthesis_whole_leaf_typed_input_scope_root_preserved":True,
        "restored_scope_root_fanout":3,
        "authority_escalation":False,
      },
      "subject_blobs":{k:sha for k,(_,sha) in FILES.items()},
      "semantic_effect":"V3_IS_ELIGIBLE_TO_SUPERSEDE_V2_FOR_WAKE_AWARE_ROOT2_SCHEDULING_WITHOUT_SUPPRESSING_THE_SEPARATE_VERIFIED_SYNTHESIS_TYPED_INPUT_SCOPE_REPAIR_ROOT",
      "authority":{"scheduling_eligibility":True,"execution":False,"promotion":False,"fresh_reality":False},
      "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
