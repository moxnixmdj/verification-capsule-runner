#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_clean_active15_promotion_20261005"
CLOSURE=SUB/"LIVEBENCH_ACTIVE15_SCOPE_REBOUND_POINTWISE_CLOSURE_20261005_V1.json"
PRE=SUB/"LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json"
EXPECTED_CLOSURE_BLOB="fa08b109378c934079e0556dab15f5451415e846"
EXPECTED_PRE_BLOB="e0c84402955425aca64b20562f3400287e8792fc"

def git_blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main()->int:
    assert git_blob(CLOSURE)==EXPECTED_CLOSURE_BLOB
    assert git_blob(PRE)==EXPECTED_PRE_BLOB
    c=json.loads(CLOSURE.read_text())
    p=json.loads(PRE.read_text())
    assert c["predicate_id"]==p["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
    assert c["status"].startswith("CANDIDATE__CLEAN_CASE_INDEPENDENT_FORMAL_PROOF_COMPOSED")
    assert p["status"]=="FROZEN_COMPOSITION_GATE__ZERO_CREDIT__INDEPENDENT_VERIFICATION_PENDING"
    f=c["verified_input_facts"]
    assert f["exact_active_scope_family_count"]==15 and f["exact_active_scope_is_active15"] is True
    assert f["excluded_legacy_family_count"]==10
    assert f["pointwise_envelope_cases"]==f["pointwise_envelope_exact_optimum_matches"]==12489
    assert f["punkt_satisfiable_contexts"]==f["punkt_satisfiable_all_pass"]==121368
    assert f["punkt_strict_lt_one_contexts"]==f["punkt_strict_lt_one_exact_single_loss"]==3112
    assert f["visible_grammar_roundtrip_cases"]==f["visible_grammar_roundtrip_passes"]==78190
    a=c["arithmetic"]
    cmp=Decimal(str(a["comparator_exact_mean_percent"]))
    bar=Decimal(str(a["registry_threshold_percent"]))
    margin=Decimal(str(a["guaranteed_margin_percentage_points"]))
    assert cmp==Decimal("65.73775") and bar==Decimal("65.7")
    assert cmp-bar==margin==Decimal("0.03775")
    fw=c["contamination_firewall"]
    assert fw["contaminated_brain_score_84_40416666666667_used_for_credit"] is False
    for k in ["target_prompt_text_read","target_response_text_read","target_rows_executed_for_this_proof","target_hidden_kwargs_read","target_instruction_id_lists_read","target_scores_read_for_brain"]:
        assert fw[k]==0, (k,fw[k])
    assert fw["comparator_public_aggregate_only"] is True
    assert c["expected_promotion"]["acceptance_credit_delta"]==1
    assert c["expected_promotion"]["dirty_replay_remains_quarantined"] is True
    assert c["supersedes_blocker"]["union25_work_required_for_exact_frozen_predicate"] is False
    fe=p["frozen_evidence"]
    assert fe["active15_scope_opening_verification"]["git_blob_sha"]=="c926e145466b812a9d6d00aca63f589f59ca2249"
    assert fe["pointwise_envelope_verification"]["git_blob_sha"]=="2284e57b4d8bdd8e7344bdab8f9a6fff221a6526"
    assert fe["punkt_context_verification"]["git_blob_sha"]=="c97465f0e3b27e2e3ad466a996c920c5a60eec5d"
    assert fe["visible_compiler_verification"]["git_blob_sha"]=="ec0de861f6dfcdf083099c3632bdd20db65991b4"
    assert "INDEPENDENT_COMPOSITION_VERIFIER_CONCLUDES_PASS" in p["precommitted_success_gate"]
    assert p["accounting"]["acceptance_credit_delta"]==0
    receipt={
      "schema":"LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PUBLIC_VERIFIER_V1",
      "status":"PASS__FROZEN_CLEAN_COMPOSITION_GATE__PREDICATE_FORCED_BY_POINTWISE_DOMINANCE",
      "predicate":"LIVEBENCH_IF_GE_65_7",
      "subject_blobs":{"closure":EXPECTED_CLOSURE_BLOB,"precommit":EXPECTED_PRE_BLOB},
      "exact_active_scope_family_count":15,
      "pointwise_envelope_exact_optimum_matches":12489,
      "punkt_satisfiable_all_pass":121368,
      "punkt_strict_lt_one_exact_single_loss":3112,
      "visible_grammar_roundtrip_passes":78190,
      "comparator_mean_percent":str(cmp),
      "threshold_percent":str(bar),
      "guaranteed_margin_percentage_points":str(margin),
      "target_rows_read_by_verifier":0,
      "target_scores_read_by_verifier":0,
      "dirty_replay_used_for_credit":False,
      "acceptance_credit_delta_authorized_if_bound":1
    }
    pathlib.Path("livebench_clean_active15_promotion_verification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
