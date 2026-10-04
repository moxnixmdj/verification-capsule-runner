#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json

SCHEMA = "LIVEBENCH_LEGACY15_HASH_OPENING_INDEPENDENT_VERIFIER_V1"

# Published by the earlier failed terminal execution before the active legacy
# identities were opened. The runner computed:
# sha256(json.dumps(sorted(unknown)).encode()).hexdigest()
EXPECTED_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

LEGACY25 = (
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "language:response_language",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
    "startend:quotation",
)

PROPOSED_ACTIVE15 = (
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
)

EXPECTED_EXCLUDED10 = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
)


def digest(values: tuple[str, ...]) -> str:
    return hashlib.sha256(json.dumps(sorted(values)).encode()).hexdigest()


def verify() -> dict:
    legacy = set(LEGACY25)
    active = set(PROPOSED_ACTIVE15)
    excluded = set(EXPECTED_EXCLUDED10)

    checks = {
        "legacy_registry_count_25": len(LEGACY25) == 25 and len(legacy) == 25,
        "active_count_15": len(PROPOSED_ACTIVE15) == 15 and len(active) == 15,
        "excluded_count_10": len(EXPECTED_EXCLUDED10) == 10 and len(excluded) == 10,
        "active_subset_of_legacy": active <= legacy,
        "excluded_is_exact_complement": excluded == legacy - active,
        "partition_disjoint": not (active & excluded),
        "partition_complete": active | excluded == legacy,
        "commitment_matches": digest(PROPOSED_ACTIVE15) == EXPECTED_COMMITMENT,
    }

    # Small adversarial neighborhood: no one-add / one-remove mutation may
    # preserve the exact published digest. This is not a collision proof; the
    # load-bearing cryptographic assumption remains SHA-256 collision resistance.
    neighbors_checked = 0
    neighbor_collision = False
    for removed in PROPOSED_ACTIVE15:
        trial = tuple(x for x in PROPOSED_ACTIVE15 if x != removed)
        neighbors_checked += 1
        neighbor_collision |= digest(trial) == EXPECTED_COMMITMENT
    for added in EXPECTED_EXCLUDED10:
        trial = PROPOSED_ACTIVE15 + (added,)
        neighbors_checked += 1
        neighbor_collision |= digest(trial) == EXPECTED_COMMITMENT
    for removed in PROPOSED_ACTIVE15:
        for added in EXPECTED_EXCLUDED10:
            trial = tuple(x for x in PROPOSED_ACTIVE15 if x != removed) + (added,)
            neighbors_checked += 1
            neighbor_collision |= digest(trial) == EXPECTED_COMMITMENT
    checks["local_mutation_collision_absent"] = not neighbor_collision

    passed = all(checks.values())
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PUBLISHED_TERMINAL_SET_COMMITMENT_OPENS_TO_PROPOSED_LEGACY15"
            if passed
            else "FAIL_CLOSED__HASH_OPENING_OR_REGISTRY_PARTITION_MISMATCH"
        ),
        "checks": checks,
        "published_commitment": EXPECTED_COMMITMENT,
        "recomputed_commitment": digest(PROPOSED_ACTIVE15),
        "legacy_registry_count": len(legacy),
        "active_id_count": len(active),
        "excluded_id_count": len(excluded),
        "active_ids": sorted(active),
        "excluded_ids": sorted(excluded),
        "neighbor_mutations_checked": neighbors_checked,
        "cryptographic_assumption": "SHA256_COLLISION_RESISTANCE",
        "terminal_dataset_read": False,
        "terminal_prompt_read": False,
        "terminal_kwargs_read": False,
        "terminal_question_id_read": False,
        "new_terminal_cases_exposed": 0,
        "acceptance_credit": 0,
        "capability_credit": 0,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"].startswith("PASS__") else 1)
