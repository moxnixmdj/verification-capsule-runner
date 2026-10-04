#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_legacy15_exact_checker_seam_20261005"
sys.path.insert(0, str(SUBJECT))

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact

EXPECTED_POSTVALIDATOR_BLOB = "b6984b26bb0df3c6e5aefd875665f61977e5e5eb"
EXPECTED_ARCHETYPE_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
RECEIPT = ROOT / "livebench_legacy15_exact_checker_seam_verification.json"


def main() -> int:
    post_path = (
        SUBJECT
        / "canonical"
        / "runtime"
        / "livebench_legacy15_exact_postvalidator_v1.py"
    )
    archetype_path = (
        SUBJECT
        / "canonical"
        / "runtime"
        / "livebench_legacy15_composition_archetypes_v1.py"
    )
    assert exact.git_blob_sha(post_path) == EXPECTED_POSTVALIDATOR_BLOB
    assert exact.git_blob_sha(archetype_path) == EXPECTED_ARCHETYPE_BLOB

    livebench_root = ROOT / "livebench-src"
    registry, binding = exact.load_pinned_registry(livebench_root)

    cases = []

    # Regression witness for a retracted false theorem:
    # Section1 has no word boundary after "Section", so it satisfies the public
    # SectionChecker while also satisfying ForbiddenWords(["section"]).
    section_contracts = [
        {
            "instruction_id": "detectable_format:multiple_sections",
            "slots": {"section_spliter": "Section", "num_sections": 3},
            "parameter_complete": True,
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["section"]},
            "parameter_complete": True,
        },
    ]
    section_out = exact.evaluate_with_registry(
        "Section1 a\nSection2 b\nSection3 c",
        section_contracts,
        registry,
    )
    assert section_out["checker_results"] == [True, True]
    cases.append({
        "id": "SECTION1_BOUNDARY_ESCAPE",
        "checker_results": section_out["checker_results"],
        "expected": [True, True],
    })

    end_contracts = [
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
            "parameter_complete": True,
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["other"]},
            "parameter_complete": True,
        },
    ]
    end_out = exact.evaluate_with_registry(
        "Any other questions?",
        end_contracts,
        registry,
    )
    assert end_out["checker_results"] == [True, False]
    cases.append({
        "id": "END_FORBIDDEN_HARD_COLLISION",
        "checker_results": end_out["checker_results"],
        "expected": [True, False],
    })

    sentence_contracts = [
        {
            "instruction_id": "length_constraints:number_sentences",
            "slots": {"num_sentences": 1, "relation": "less than"},
            "parameter_complete": True,
        },
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
            "parameter_complete": True,
        },
    ]
    sentence_out = exact.evaluate_with_registry(
        "Any other questions?",
        sentence_contracts,
        registry,
    )
    assert sentence_out["checker_results"] == [False, True]
    cases.append({
        "id": "SENTENCE_LT_ONE_END_COLLISION_WITNESS",
        "checker_results": sentence_out["checker_results"],
        "expected": [False, True],
    })

    missing_slots_fail_closed = False
    try:
        exact.evaluate_with_registry(
            "x",
            [{
                "instruction_id": "startend:end_checker",
                "slots": {},
                "parameter_complete": True,
            }],
            registry,
        )
    except exact.ExactPostvalidationError as exc:
        missing_slots_fail_closed = "VISIBLE_SLOT_SHAPE_MISMATCH" in str(exc)
    assert missing_slots_fail_closed

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_POSTVALIDATOR_PUBLIC_VERIFICATION_20261005_V1",
        "status": "PASS__EXACT_PINNED_CHECKER_BYTES__VISIBLE_SLOTS_ONLY__FALSE_SECTION_UNSAT_REJECTED",
        "subject": {
            "postvalidator_git_blob_sha": EXPECTED_POSTVALIDATOR_BLOB,
            "archetype_git_blob_sha": EXPECTED_ARCHETYPE_BLOB,
        },
        "pinned_source": binding,
        "cases": cases,
        "missing_visible_slots_fail_closed": missing_slots_fail_closed,
        "terminal_rows_read": 0,
        "terminal_prompts_read": 0,
        "hidden_kwargs_read": 0,
        "comparator_responses_read": 0,
        "acceptance_credit": False,
    }
    RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
