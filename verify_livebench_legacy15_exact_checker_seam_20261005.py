#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_legacy15_exact_checker_seam_20261005"
sys.path.insert(0, str(SUBJECT))

import livebench_legacy15_exact_contract_checker_v1 as exact

EXPECTED_SUBJECT_BLOB = "d9fdc2f1faa629cea99eb8e51b82bae8f71f6672"
RECEIPT = ROOT / "livebench_legacy15_exact_checker_seam_verification.json"


def blob(path: Path) -> str:
    return exact.git_blob_sha(path.read_bytes())


def main() -> int:
    subject_path = SUBJECT / "livebench_legacy15_exact_contract_checker_v1.py"
    assert blob(subject_path) == EXPECTED_SUBJECT_BLOB

    livebench_root = ROOT / "livebench-src"
    bound = exact.verify_pinned_source(livebench_root)
    registry = exact.load_pinned_registry(livebench_root)

    cases = []

    # Critical truth-repair witness: Section1 is accepted by the pinned section
    # checker and does NOT trip ForbiddenWords("section"). Therefore the old
    # section+forbidden UNSAT theorem is false and must stay retracted.
    section_contracts = [
        {
            "instruction_id": "detectable_format:multiple_sections",
            "slots": {"section_spliter": "Section", "num_sections": 3},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["section"]},
        },
    ]
    section_response = "Section1 a\nSection2 b\nSection3 c"
    section_flags = exact.evaluate_with_registry(
        section_response, section_contracts, registry
    )
    assert section_flags == (True, True)
    cases.append({
        "id": "SECTION1_BOUNDARY_ESCAPE",
        "checker_results": list(section_flags),
        "expected": [True, True],
    })

    end_contracts = [
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["other"]},
        },
    ]
    end_flags = exact.evaluate_with_registry(
        "Any other questions?", end_contracts, registry
    )
    assert end_flags == (True, False)
    cases.append({
        "id": "END_FORBIDDEN_HARD_COLLISION",
        "checker_results": list(end_flags),
        "expected": [True, False],
    })

    sentence_contracts = [
        {
            "instruction_id": "length_constraints:number_sentences",
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": "Any other questions?"},
        },
    ]
    sentence_flags = exact.evaluate_with_registry(
        "Any other questions?", sentence_contracts, registry
    )
    assert sentence_flags == (False, True)
    cases.append({
        "id": "SENTENCE_LT_ONE_END_COLLISION_WITNESS",
        "checker_results": list(sentence_flags),
        "expected": [False, True],
    })

    exact_shape_failure = False
    try:
        exact.evaluate_with_registry(
            "x",
            [{"instruction_id": "startend:end_checker", "slots": {}}],
            registry,
        )
    except exact.ExactContractCheckerError:
        exact_shape_failure = True
    assert exact_shape_failure

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_CHECKER_SEAM_PUBLIC_VERIFICATION_20261005_V1",
        "status": "PASS__EXACT_PINNED_CHECKER_BYTES__VISIBLE_SLOTS_ONLY__FALSE_SECTION_UNSAT_REJECTED",
        "subject_git_blob_sha": EXPECTED_SUBJECT_BLOB,
        "pinned_source": bound,
        "cases": cases,
        "missing_visible_slots_fail_closed": exact_shape_failure,
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
