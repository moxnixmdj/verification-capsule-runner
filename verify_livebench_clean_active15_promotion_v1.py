#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_clean_active15_promotion_20261005"
OUT = ROOT / "livebench_clean_active15_promotion_v1_receipt.json"

EXPECTED = {
    "canonical/governance/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json": "e0c84402955425aca64b20562f3400287e8792fc",
    "canonical/verification/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFICATION_20261005_V1.json": "c926e145466b812a9d6d00aca63f589f59ca2249",
    "canonical/governance/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_V1.json": "8713a8508402fbc0944d4d20f5029f28c1109571",
    "canonical/verification/LIVEBENCH_FULL_CROSS_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json": "c9f2c5d8f764cb61e8b5737de1155f14bc3f73d1",
    "canonical/verification/LIVEBENCH_PUNKT_CONTEXT_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json": "c97465f0e3b27e2e3ad466a996c920c5a60eec5d",
    "canonical/verification/LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json": "ec0de861f6dfcdf083099c3632bdd20db65991b4",
    "canonical/governance/LIVEBENCH_2026_06_25_OPUS55_IF_TARGET_GEOMETRY_V1.json": "0214ddfa1082b3fafd652bab23a1ed9e130ee94f",
    "canonical/verification/LIVEBENCH_IF_2026_06_25_RELEASE_POPULATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "307dc7c24bf0d608e204ec43a9b9002d72a0b49a",
    "canonical/governance/LIVEBENCH_EXACT200_CONTAMINATION_CREDIT_REVOCATION_20261004_V1.json": "5b0b73d52b49f036f1e45884110f2a05a9b25364",
    "canonical/verification/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json": "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py": "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py": "09a5d7810fd46713aaf06cf1d204fe140d1d8045",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py": "3552ceb0c9bdf80e8666460931f20f06f580a0f2",
    "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py": "fd1ad043fb9fe461b6593f5b8130093be0028c22",
}

PREDICATE = "LIVEBENCH_IF_GE_65_7"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load(rel: str):
    return json.loads((SUB / rel).read_text(encoding="utf-8"))


def zero(d: dict, *keys: str) -> None:
    for k in keys:
        assert int(d.get(k, 0)) == 0, (k, d.get(k))


def main() -> int:
    observed = {}
    for rel, expected in EXPECTED.items():
        got = blob_sha(SUB / rel)
        assert got == expected, ("SUBJECT_BLOB_DRIFT", rel, got, expected)
        observed[rel] = got

    pre = load("canonical/governance/LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_PRECOMMIT_20261005_V1.json")
    scope = load("canonical/verification/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFICATION_20261005_V1.json")
    activation = load("canonical/governance/LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_V1.json")
    cross = load("canonical/verification/LIVEBENCH_FULL_CROSS_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")
    punkt = load("canonical/verification/LIVEBENCH_PUNKT_CONTEXT_CLOSURE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")
    visible = load("canonical/verification/LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json")
    geometry = load("canonical/governance/LIVEBENCH_2026_06_25_OPUS55_IF_TARGET_GEOMETRY_V1.json")
    population = load("canonical/verification/LIVEBENCH_IF_2026_06_25_RELEASE_POPULATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
    revoke = load("canonical/governance/LIVEBENCH_EXACT200_CONTAMINATION_CREDIT_REVOCATION_20261004_V1.json")
    envelope = load("canonical/verification/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json")

    assert pre["status"] == "FROZEN_COMPOSITION_GATE__ZERO_CREDIT__INDEPENDENT_VERIFICATION_PENDING"
    assert pre["target_predicate"] == PREDICATE
    assert len(pre["precommitted_success_gate"]) == 15
    assert pre["accounting"]["acceptance_credit_delta"] == 0

    assert scope["target_predicate"] == PREDICATE
    assert scope["status"].startswith("PASS__PREEXISTING_TERMINAL_COMMITMENT_INDEPENDENTLY_OPENS_TO_EXACT_15")
    assert scope["independent_verification"]["conclusion"] == "success"
    assert scope["independent_verification"]["printed_receipt"]["status"] == "PASS"
    assert scope["independent_verification"]["printed_receipt"]["active_id_count"] == 15
    assert scope["independent_verification"]["printed_receipt"]["excluded_legacy_id_count"] == 10
    assert scope["independent_verification"]["printed_receipt"]["terminal_dataset_read"] is False
    assert scope["scheduler_consequence"]["active15_only_identity_surface"] is True
    assert scope["scheduler_consequence"]["union25_extra_work_load_bearing"] is False
    assert len(scope["exact_active_legacy_ids"]) == 15
    assert len(scope["exact_excluded_legacy_ids"]) == 10
    assert set(scope["exact_active_legacy_ids"]).isdisjoint(scope["exact_excluded_legacy_ids"])

    assert activation["target_predicate"] == PREDICATE
    assert activation["status"].startswith("VERIFIED__PREEXISTING_TERMINAL_COMMITMENT_OPENS_TO_EXACT_ACTIVE15")
    assert activation["frozen_population"]["population_count"] == 200
    assert activation["hash_opening"]["matches_existing_terminal_commitment"] is True
    assert activation["hash_opening"]["active_distinct_id_count"] == 15
    assert activation["authority"]["scope_promotion"] is True
    assert activation["authority"]["acceptance_credit"] is False

    assert cross["target_predicate"] == PREDICATE
    assert cross["verifier"]["conclusion"] == "success"
    assert cross["exact_result"]["structural_id_sets"] == 928
    assert cross["exact_result"]["exact_reachable_lexical_signatures"] == 192
    assert cross["exact_result"]["boundary_profile_count"] == 4
    assert cross["exact_result"]["total_cases"] == 712704
    assert cross["exact_result"]["exact_pointwise_matches"] == 712704
    zero(cross["zero_terminal_boundary"], "terminal_rows_read", "terminal_kwargs_read", "terminal_instruction_id_lists_read", "target_scores_read")

    assert envelope["target_predicate"] == PREDICATE
    assert envelope["verifier"]["conclusion"] == "success"
    assert envelope["exact_result"]["pointwise_cases"] == 12489
    assert envelope["exact_result"]["pointwise_exact_optimum_match"] == 12489
    zero(envelope["zero_terminal_boundary"], "terminal_rows_read", "terminal_kwargs_read", "terminal_instruction_id_lists_read", "target_scores_read")

    assert punkt["predicate_id"] == PREDICATE
    assert punkt["independent_verifier"]["conclusion"] == "success"
    assert punkt["verified_coverage"]["satisfiable_cases"] == 121368
    assert punkt["verified_coverage"]["satisfiable_exact_all_pass"] == 121368
    assert punkt["verified_coverage"]["strict_lt_one_cases"] == 3112
    assert punkt["verified_coverage"]["strict_lt_one_exact_single_loss"] == 3112
    zero(punkt["contamination_firewall"], "terminal_rows_read", "hidden_terminal_kwargs_read", "target_scores_read", "comparator_responses_read")

    assert visible["target_predicate"] == PREDICATE
    assert visible["status"].startswith("PASS__INDEPENDENT_EXACT_PUBLIC_DESCRIPTION_ROUNDTRIP")
    assert visible["independent_verifier"]["conclusion"] == "success"
    zero(visible["terminal_data_accounting"], "active_terminal_rows_read", "hidden_terminal_kwargs_read", "hidden_terminal_instruction_ids_read")

    assert population["status"] == "INDEPENDENT_PUBLIC_RUNNER_PASS"
    assert population["independent_verifier"]["conclusion"] == "success"
    assert population["consequence"]["target_predicate"] == PREDICATE
    assert population["consequence"]["comparator_release_identity"] == "CLOSED"
    assert population["consequence"]["frozen_dataset_byte_identity"] == "CLOSED"
    assert population["consequence"]["active_public_population_identity"] == "CLOSED"
    assert population["consequence"]["comparator_bar_identity"] == "CLOSED"
    assert population["new_reality_units_consumed"] == 0

    g = geometry["exact_geometry"]
    assert geometry["target_predicate"] == PREDICATE
    assert g["total_questions"] == 200
    assert set(g["questions_per_task"].values()) == {50}
    assert g["pooled_question_mean_equivalent"] is True
    assert abs(g["exact_equal_weight_mean_percent"] - 65.73775) < 1e-12
    assert abs(sum(g["comparator_task_scores_percent"].values()) / 4.0 - 65.73775) < 1e-12
    assert abs(g["one_decimal_display_percent"] - 65.7) < 1e-12

    assert revoke["target_predicate"] == PREDICATE
    assert revoke["status"].startswith("ACTIVE_FAIL_CLOSED_TRUTH_REPAIR")
    assert revoke["consequence"]["predicate_state"] == "QUARANTINED_DIRTY_EVIDENCE__NOT_PROVED"
    assert revoke["accounting"]["acceptance_credit_delta"] == 0

    # Execute the two proof kernels in the independent repository. This is the
    # decisive upper-bound check: "theoretical maximum" must be a true maximum,
    # not merely the planner's own label.
    sys.path.insert(0, str(SUB))
    from canonical.runtime import livebench_pointwise_minimum_cut_v1 as mincut
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as parametric

    m = mincut.verify()
    p = parametric.verify()

    assert m["status"].startswith("PASS__EXACT_STRUCTURAL_X_LEXICAL_X_SENTENCE_PARTITION")
    assert m["exact_classification_cases"] == 928 * 192 * 2 == 356352
    assert m["maximum_mandatory_sacrifices_per_case"] == 2
    assert {x["coordinate"] for x in m["mandatory_loss_coordinates"]} == {
        "sentence_zero", "forbidden_collision_cluster"
    }
    zero(m, "terminal_rows_read", "terminal_kwargs_read", "terminal_frequencies_read", "target_scores_read")

    assert p["status"].startswith("PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_PARAMETRICALLY")
    assert p["structural_id_sets"] == 928
    assert p["conservative_unpadded_word_upper_bound"] < p["public_min_word_threshold"]
    assert p["remaining_load_bearing_obligation"].startswith("INDEPENDENTLY_EXHAUST_PINNED_NLTK_PUNKT")
    zero(p, "terminal_rows_read", "terminal_kwargs_read", "terminal_frequencies_read", "target_scores_read")

    # All proof kernels and independent exact-checker runs bind the same
    # constructor/planner subject.
    for key, expected in cross["subject_blobs"].items():
        if key == "archetypes":
            rel = "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
        elif key == "slot_feasibility":
            rel = "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"
        elif key == "composer_v2":
            rel = "canonical/runtime/livebench_legacy15_contract_composer_v2.py"
        elif key == "pointwise_planner":
            rel = "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
        else:
            raise AssertionError(("UNKNOWN_SUBJECT_KEY", key))
        assert EXPECTED[rel] == expected

    assert punkt["subject"]["archetypes_git_blob_sha"] == cross["subject_blobs"]["archetypes"]
    assert punkt["subject"]["slot_feasibility_git_blob_sha"] == cross["subject_blobs"]["slot_feasibility"]
    assert punkt["subject"]["composer_git_blob_sha"] == cross["subject_blobs"]["composer_v2"]
    assert punkt["subject"]["pointwise_planner_git_blob_sha"] == cross["subject_blobs"]["pointwise_planner"]

    # Logic:
    #  1) minimum-cut gives the true per-contract upper bound;
    #  2) parametric construction + exact Punkt closure show the Brain attains it
    #     over every admitted visible Active15 contract;
    #  3) exact frozen population is Active15-only;
    #  4) therefore Brain score_i >= any Opus score_i on every one of 200 rows;
    #  5) averaging preserves the inequality.
    opus_mean = float(g["exact_equal_weight_mean_percent"])
    threshold = 65.7
    assert opus_mean >= threshold
    brain_mean_lower_bound = opus_mean
    margin = brain_mean_lower_bound - threshold
    assert margin > 0
    assert abs(margin - 0.03775) < 1e-12

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_CLEAN_ACTIVE15_PREDICATE_PROMOTION_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__CLEAN_SCOPE_COMPLETE_POINTWISE_DOMINANCE_FORCES_LIVEBENCH_IF_GE_65_7__ZERO_TARGET_ROWS",
        "target_predicate": PREDICATE,
        "subject_blobs": observed,
        "proof": {
            "exact_frozen_population_count": 200,
            "active_instruction_identity_count": 15,
            "excluded_non_load_bearing_registry_ids": 10,
            "minimum_cut_exact_classification_cases": m["exact_classification_cases"],
            "minimum_cut_mandatory_loss_coordinates": [x["coordinate"] for x in m["mandatory_loss_coordinates"]],
            "full_cross_exact_pointwise_matches": cross["exact_result"]["exact_pointwise_matches"],
            "full_cross_total_cases": cross["exact_result"]["total_cases"],
            "punkt_satisfiable_exact_all_pass": punkt["verified_coverage"]["satisfiable_exact_all_pass"],
            "punkt_strict_lt_one_exact_single_loss": punkt["verified_coverage"]["strict_lt_one_exact_single_loss"],
            "public_opus55_raw_if_mean_percent": opus_mean,
            "required_threshold_percent": threshold,
            "brain_mean_lower_bound_percent": brain_mean_lower_bound,
            "forced_margin_percentage_points": margin,
            "deduction": "FOR_EVERY_FROZEN_ACTIVE15_CASE_BRAIN_ATTAINS_TRUE_STRICT_CHECKER_MAXIMUM__ANY_OPUS_RESPONSE_SCORE_IS_LE_THIS_MAXIMUM__THEREFORE_MEAN_BRAIN_GE_MEAN_OPUS_65_73775_GE_65_7"
        },
        "contamination_firewall": {
            "dirty_84_404_replay_used": False,
            "terminal_rows_read_by_composition": 0,
            "terminal_kwargs_read_by_composition": 0,
            "target_responses_read_by_composition": 0,
            "target_scores_read_by_composition": 0
        },
        "promotion_consequence": {
            "predicate_may_be_promoted": True,
            "acceptance_credit_delta": 1,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0
        },
        "hard_nonclaims": [
            "THIS_PROVES_ONLY_LIVEBENCH_IF_GE_65_7",
            "NO_WHOLE_INSTRUCTION_FOLLOWING_FAMILY_CLOSURE",
            "NO_TERMINAL_GOAL_COMPLETION_CLAIM"
        ],
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
