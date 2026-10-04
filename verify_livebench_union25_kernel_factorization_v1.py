#!/usr/bin/env python3
"""Independent exact-source verifier for the union25 extension-kernel factorization."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import sys

PINNED_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"

ACTIVE15 = {
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "startend:quotation",
}

COMMUTING4 = (
    "keywords:letter_frequency",
    "detectable_content:number_placeholders",
    "detectable_format:number_highlighted_sections",
    "punctuation:no_comma",
)
SEMANTIC_AXIS5 = (
    "keywords:frequency",
    "language:response_language",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
)
CONSTRAINED = "detectable_format:constrained_response"


def powerset(values):
    for n in range(len(values) + 1):
        yield from combinations(values, n)


def main(root: str) -> dict:
    lb = Path(root).resolve()
    sys.path.insert(0, str(lb / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_registry as registry
    from instruction_following_eval import instructions

    all_ids = tuple(registry.INSTRUCTION_DICT.keys())
    if len(all_ids) != 25:
        raise AssertionError(("REGISTRY_COUNT", len(all_ids)))
    extra10 = set(all_ids) - ACTIVE15
    if len(extra10) != 10:
        raise AssertionError(("EXTRA10_COUNT", len(extra10), sorted(extra10)))

    conflicts = registry.INSTRUCTION_CONFLICTS

    def compatible(ids):
        ids = tuple(ids)
        return all(b not in conflicts[a] for a, b in combinations(ids, 2))

    sets = []
    for n in range(1, 6):
        sets.extend(x for x in combinations(all_ids, n) if compatible(x))
    if len(sets) != 14559:
        raise AssertionError(("COMPATIBLE_TOTAL", len(sets)))

    signatures = {
        tuple(iid for iid in all_ids if iid in set(ids) and iid in extra10)
        for ids in sets
        if set(ids) & extra10
    }
    if len(signatures) != 156:
        raise AssertionError(("EXTRA_SIGNATURE_COUNT", len(signatures)))

    # Verify the proposed graph-free factor directly against the exact imported
    # registry, not against Brain's reimplementation.
    for modifier in COMMUTING4:
        other_extra_conflicts = (set(conflicts[modifier]) & extra10) - {modifier}
        if other_extra_conflicts:
            raise AssertionError(
                ("COMMUTING_EDGE_DRIFT", modifier, sorted(other_extra_conflicts))
            )

    axis_states = tuple(x for x in powerset(SEMANTIC_AXIS5) if compatible(x))
    expected_axis_states = (
        (),
        ("keywords:frequency",),
        ("language:response_language",),
        ("change_case:capital_word_frequency",),
        ("change_case:english_capital",),
        ("change_case:english_lowercase",),
        ("keywords:frequency", "change_case:capital_word_frequency"),
        ("keywords:frequency", "change_case:english_capital"),
        ("keywords:frequency", "change_case:english_lowercase"),
        ("language:response_language", "change_case:capital_word_frequency"),
    )
    if axis_states != expected_axis_states:
        raise AssertionError(("AXIS_STATES", axis_states))

    if set(conflicts[CONSTRAINED]) != set(all_ids):
        raise AssertionError("CONSTRAINED_NOT_ISOLATED")

    product_pairs = set()
    isolated = 0
    for sig in signatures:
        s = set(sig)
        if CONSTRAINED in s:
            if s != {CONSTRAINED}:
                raise AssertionError(("BAD_CONSTRAINED_SIGNATURE", sig))
            isolated += 1
            continue
        axis = tuple(i for i in SEMANTIC_AXIS5 if i in s)
        mods = tuple(i for i in COMMUTING4 if i in s)
        if set(axis) | set(mods) != s:
            raise AssertionError(("PARTITION_DRIFT", sig))
        product_pairs.add((axis, mods))

    if isolated != 1 or len(product_pairs) != 155:
        raise AssertionError(("PRODUCT_COUNT", isolated, len(product_pairs)))

    # Verify source constants behind the numeric-format word-margin lemma.
    if instructions._NUM_PLACEHOLDERS != 4:
        raise AssertionError(("PLACEHOLDER_MAX", instructions._NUM_PLACEHOLDERS))
    if instructions._NUM_HIGHLIGHTED_SECTIONS != 4:
        raise AssertionError(("HIGHLIGHT_MAX", instructions._NUM_HIGHLIGHTED_SECTIONS))
    if instructions._NUM_WORDS_LOWER_LIMIT != 100:
        raise AssertionError(("WORD_MIN", instructions._NUM_WORDS_LOWER_LIMIT))

    by_sig_size = Counter(map(len, signatures))
    result = {
        "status": "INDEPENDENT_PASS__UNION25_DELTA10_FACTORIZATION",
        "pinned_livebench_commit": PINNED_COMMIT,
        "registry_family_count": len(all_ids),
        "compatible_structural_sets_1_to_5": len(sets),
        "extra10_signature_count": len(signatures),
        "isolated_constrained_signature_count": isolated,
        "nonconstrained_product_signature_count": len(product_pairs),
        "semantic_axis_state_count_including_empty": len(axis_states),
        "semantic_axis_nonempty_state_count": len(axis_states) - 1,
        "semantic_axis_size_histogram": dict(sorted(Counter(map(len, axis_states)).items())),
        "commuting_modifier_count": len(COMMUTING4),
        "extra_signature_size_histogram": dict(sorted(by_sig_size.items())),
        "closed_form": "15 + 80 + 60 + 1 = 156",
        "source_constants": {
            "max_placeholders": instructions._NUM_PLACEHOLDERS,
            "max_highlights": instructions._NUM_HIGHLIGHTED_SECTIONS,
            "min_word_threshold": instructions._NUM_WORDS_LOWER_LIMIT,
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
    }
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_livebench_union25_kernel_factorization_v1.py LIVEBENCH_ROOT")
    main(sys.argv[1])
