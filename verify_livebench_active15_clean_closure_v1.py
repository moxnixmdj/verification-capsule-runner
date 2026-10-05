#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_active15_clean_closure_20261005"

FILES = {
    "canonical/governance/LIVEBENCH_ACTIVE15_SCOPE_REBOUND_POINTWISE_CLOSURE_20261005_V1.json":
        "fa08b109378c934079e0556dab15f5451415e846",
    "canonical/verification/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFICATION_20261005_V1.json":
        "c926e145466b812a9d6d00aca63f589f59ca2249",
    "canonical/governance/LIVEBENCH_CASE_INDEPENDENT_POINTWISE_DOMINANCE_THEOREM_20261005_V1.json":
        "3cb051d106d9589c98620e6d8c2d9f127512ad6c",
    "canonical/verification/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json":
        "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526",
    "canonical/verification/LIVEBENCH_PUNKT_CONTEXT_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json":
        "c97465f0e3b27e2e3ad466a996c920c5a60eec5d",
    "canonical/verification/LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json":
        "ec0de861f6dfcdf083099c3632bdd20db65991b4",
    "canonical/governance/LIVEBENCH_2026_06_25_OPUS55_IF_TARGET_GEOMETRY_V1.json":
        "0214ddfa1082b3fafd652bab23a1ed9e130ee94f",
    "canonical/governance/LIVEBENCH_EXACT200_CONTAMINATION_CREDIT_REVOCATION_20261004_V1.json":
        "5b0b73d52b49f036f1e45884110f2a05a9b25364",
}
PREDICATE = "LIVEBENCH_IF_GE_65_7"
ACTIVE15 = {
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
}
ADMISSIBLE_RESCUE = (
    "CASE_INDEPENDENT_FORMAL_OR_UNIVERSAL_PROOF_FROM_FROZEN_CHECKER_SEMANTICS_WITHOUT_TARGET_ROW_DEPENDENCE"
)

def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(rel: str):
    return json.loads((SUBJECT / rel).read_text(encoding="utf-8"))

def main() -> int:
    observed = {rel: git_blob(SUBJECT / rel) for rel in FILES}
    assert observed == FILES, (observed, FILES)

    closure = load("canonical/governance/LIVEBENCH_ACTIVE15_SCOPE_REBOUND_POINTWISE_CLOSURE_20261005_V1.json")
    scope = load("canonical/verification/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFICATION_20261005_V1.json")
    theorem = load("canonical/governance/LIVEBENCH_CASE_INDEPENDENT_POINTWISE_DOMINANCE_THEOREM_20261005_V1.json")
    envelope = load("canonical/verification/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")
    punkt = load("canonical/verification/LIVEBENCH_PUNKT_CONTEXT_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")
    grammar = load("canonical/verification/LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json")
    geometry = load("canonical/governance/LIVEBENCH_2026_06_25_OPUS55_IF_TARGET_GEOMETRY_V1.json")
    revocation = load("canonical/governance/LIVEBENCH_EXACT200_CONTAMINATION_CREDIT_REVOCATION_20261004_V1.json")

    assert closure["predicate_id"] == PREDICATE
    assert scope["target_predicate"] == PREDICATE
    assert theorem["predicate_id"] == PREDICATE
    assert envelope["target_predicate"] == PREDICATE
    assert punkt["predicate_id"] == PREDICATE
    assert grammar["target_predicate"] == PREDICATE
    assert geometry["target_predicate"] == PREDICATE
    assert revocation["predicate_id"] == PREDICATE

    # Exact scope opening independently binds the frozen population to Active15.
    assert scope["status"].startswith("PASS__")
    assert scope["independent_verification"]["conclusion"] == "success"
    assert scope["commitment_provenance"]["commitment_created_before_opening"] is True
    assert set(scope["exact_active_legacy_ids"]) == ACTIVE15
    assert len(scope["exact_active_legacy_ids"]) == 15
    assert len(scope["exact_excluded_legacy_ids"]) == 10
    assert scope["scheduler_consequence"]["active15_only_identity_surface"] is True
    assert scope["scheduler_consequence"]["union25_extra_work_load_bearing"] is False

    # The old theorem's sole scope blocker is exactly what the opening discharges.
    assert theorem["status"].startswith("CANDIDATE__ACTIVE15_POINTWISE_DOMINANCE_CHAIN_CLOSED")
    assert theorem["candidate_consequence"]["blocked_on"] == "UNION25_SCOPE_CLOSURE_OR_EXACT_RELEASE_SCOPE_BRIDGE"
    assert theorem["scope_correction"]["consequence"].endswith(
        "WITHOUT_EITHER_AN_INDEPENDENT_EXACT_RELEASE_SCOPE_BRIDGE_TO_ACTIVE15_OR_POINTWISE_CLOSURE_OVER_PUBLIC_UNION25"
    )

    # Independent proof stack.
    assert envelope["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__")
    ex = envelope["exact_result"]
    assert ex["total_cases"] == 12489
    assert ex["pointwise_exact_optimum_match"] == 12489

    assert punkt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__")
    pc = punkt["verified_coverage"]
    assert pc["satisfiable_cases"] == pc["satisfiable_exact_all_pass"] == 121368
    assert pc["strict_lt_one_cases"] == pc["strict_lt_one_exact_single_loss"] == 3112

    assert grammar["status"].startswith("PASS__INDEPENDENT_")
    gc = grammar["coverage"]
    assert gc["exact_roundtrip_cases"] == gc["exact_roundtrip_passes"] == 78190
    assert gc["structural_sets"] == 928
    assert gc["structural_order_permutations"] == 51385

    # Recompute the public comparator bar rather than trusting the composed number.
    geom = geometry["exact_geometry"]
    scores = geom["comparator_task_scores_percent"]
    assert set(scores) == {"paraphrase", "simplify", "story_generation", "summarize"}
    assert set(geom["questions_per_task"].values()) == {50}
    assert geom["total_questions"] == 200
    mean = sum(scores.values()) / len(scores)
    assert abs(mean - 65.73775) < 1e-12
    assert abs(mean - geom["exact_equal_weight_mean_percent"]) < 1e-12
    threshold = float(closure["arithmetic"]["registry_threshold_percent"])
    assert threshold == 65.7
    assert mean >= threshold
    margin = mean - threshold
    assert abs(margin - 0.03775) < 1e-12

    # The proof uses the specifically authorized clean formal rescue class, never the dirty replay.
    assert "CREDIT_REVOKED" in revocation["status"]
    assert ADMISSIBLE_RESCUE in revocation["admissible_rescue"]
    fw = closure["contamination_firewall"]
    assert fw["contaminated_brain_score_84_40416666666667_used_for_credit"] is False
    assert fw["target_rows_executed_for_this_proof"] == 0
    assert fw["target_prompt_text_read"] == 0
    assert fw["target_response_text_read"] == 0
    assert fw["target_hidden_kwargs_read"] == 0
    assert fw["target_instruction_id_lists_read"] == 0
    assert fw["target_scores_read_for_brain"] == 0
    assert fw["admissible_rescue_class"] == ADMISSIBLE_RESCUE

    # Composition theorem: exact scope + universal pointwise maximum => aggregate noninferiority.
    assert closure["supersedes_blocker"]["union25_work_required_for_exact_frozen_predicate"] is False
    assert closure["expected_promotion"]["predicate_state"] == "PROVED__CLEAN_CASE_INDEPENDENT_FORMAL_POINTWISE_DOMINANCE"
    assert closure["expected_promotion"]["acceptance_credit_delta"] == 1

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_CLEAN_CLOSURE_PUBLIC_VERIFIER_V1",
        "status": "PASS__EXACT_ACTIVE15_SCOPE_REBINDS_INDEPENDENT_POINTWISE_DOMINANCE__BRAIN_MEAN_GE_OPUS_65_73775_GE_65_7__ZERO_TERMINAL_REPLAY",
        "predicate_id": PREDICATE,
        "subject_blobs": observed,
        "scope": {
            "exact_active_id_count": 15,
            "excluded_legacy_id_count": 10,
            "preexisting_commitment": True,
            "independent_opening": True,
        },
        "proof_stack": {
            "pointwise_envelope_exact_optimum": "12489/12489",
            "punkt_satisfiable_all_pass": "121368/121368",
            "punkt_lt1_exact_single_loss": "3112/3112",
            "visible_grammar_roundtrip": "78190/78190",
            "structural_sets": 928,
            "structural_orderings": 51385,
        },
        "arithmetic": {
            "opus_public_mean_percent": mean,
            "fixed_threshold_percent": threshold,
            "guaranteed_margin_percentage_points": margin,
        },
        "logical_conclusion": (
            "FOR_EVERY_EXACT_FROZEN_CASE_BRAIN_POINTWISE_SCORE_GE_OPUS_POINTWISE_SCORE"
            "__THEREFORE_MEAN_BRAIN_GE_MEAN_OPUS_65_73775_GE_65_7"
        ),
        "contamination": {
            "target_rows_executed": 0,
            "target_prompt_text_read": 0,
            "target_response_text_read": 0,
            "target_hidden_kwargs_read": 0,
            "target_instruction_id_lists_read": 0,
            "dirty_84_404_score_used_for_credit": False,
            "rescue_class": ADMISSIBLE_RESCUE,
        },
        "promotion": {
            "predicate_state": "PROVED__CLEAN_CASE_INDEPENDENT_FORMAL_POINTWISE_DOMINANCE",
            "acceptance_credit_delta": 1,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    out = ROOT / "livebench_active15_clean_closure_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
