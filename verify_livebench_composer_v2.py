#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import traceback
from collections import Counter
from itertools import combinations, product

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_sentence_wrapper_closure_20261005"
RUNTIME = SUBJECT / "canonical/runtime"

EXPECTED_BLOBS = {
    "livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "livebench_legacy15_sentence_wrapper_closure_v1.py":
        "a4d83e0963df023273218382fe77cf7a5f9f7822",
}
OUT = ROOT / "livebench_composer_v2_verification.json"
QUOTIENT_SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
QUOTIENT_PROOF = QUOTIENT_SUBJECT / "canonical/runtime/livebench_legacy15_full_semantic_quotient_v1.py"
QUOTIENT_PROOF_BLOB = "f21a5bec868575974f6b1a47573cb30460f82778"



def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def write(payload: dict) -> None:
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )



def independent_quotient_audit() -> dict:
    """Re-derive the optimum quotient from pinned public source, not subject logic."""
    live_if = pathlib.Path("/tmp/LiveBench/livebench/if_runner")
    if str(live_if) not in sys.path:
        sys.path.insert(0, str(live_if))

    from instruction_following_eval import instructions
    from instruction_following_eval import instructions_registry
    from instruction_following_eval import instructions_util

    active = (
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
    active_set = set(active)
    conflicts = set()
    for left, rights in instructions_registry.INSTRUCTION_CONFLICTS.items():
        for right in rights:
            if left in active_set and right in active_set and left != right:
                conflicts.add(frozenset((left, right)))

    def compatible(ids):
        ss = set(ids)
        return not any(pair <= ss for pair in conflicts)

    id_sets = tuple(
        ids
        for k in range(1, 6)
        for ids in combinations(active, k)
        if compatible(ids)
    )
    assert len(id_sets) == 928, len(id_sets)

    FORB = "keywords:forbidden_words"
    NTH = "length_constraints:nth_paragraph_first_word"
    END = "startend:end_checker"
    SENT = "length_constraints:number_sentences"
    REPEAT = "combination:repeat_prompt"
    EXIST = "keywords:existence"
    TITLE = "detectable_format:title"
    JSON_ID = "detectable_format:json_format"
    TWO = "combination:two_responses"

    repeat_sets = [set(x) for x in id_sets if REPEAT in x]
    json_sets = [set(x) for x in id_sets if JSON_ID in x]
    two_sets = [set(x) for x in id_sets if TWO in x]
    assert len(repeat_sets) == 4 and all(x <= {REPEAT, EXIST, TITLE} for x in repeat_sets)
    assert len(json_sets) == 4 and all(x <= {JSON_ID, EXIST, FORB} for x in json_sets)
    assert len(two_sets) == 8 and all(x <= {TWO, EXIST, FORB, TITLE} for x in two_sets)

    words = tuple(str(x) for x in instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(w.isascii() and w.isalpha() for w in words)
    assert instructions._NUM_KEYWORDS == 5
    assert instructions._NUM_WORDS_LOWER_LIMIT == 100
    assert instructions._NUM_WORDS_UPPER_LIMIT == 500
    assert instructions._MAX_NUM_SENTENCES == 20
    assert instructions._NUM_PARAGRAPHS == 5
    assert instructions._NUM_BULLETS == 5
    assert instructions._NUM_SECTIONS == 5
    assert tuple(instructions._SECTION_SPLITER) == ("Section", "SECTION")
    assert tuple(instructions._POSTSCRIPT_MARKER) == ("P.S.", "P.P.S")

    end_phrases = tuple(instructions._ENDING_OPTIONS)
    assert len(end_phrases) == 2
    word_set = {w.casefold() for w in words}
    end_word_sets = tuple(
        {x.casefold() for x in re.findall(r"[A-Za-z]+", phrase)}
        for phrase in end_phrases
    )
    special = tuple(sorted(word_set & set().union(*end_word_sets)))
    assert special == ("anything", "can", "help", "other")
    assert not ({"p", "s"} & word_set)

    sigs = []
    nth_categories = special + ("ALL_OTHER",)
    for nth_category in nth_categories:
        for end_index in range(2):
            for raw_bits in product((False, True), repeat=5):
                nth_forbidden = bool(raw_bits[0])
                bits = dict(zip(special, map(bool, raw_bits[1:])))
                if nth_category != "ALL_OTHER" and nth_forbidden != bits[nth_category]:
                    continue
                sigs.append((nth_category, nth_forbidden, bits, end_index))
    assert len(sigs) == 192
    assert len({
        (a, b, tuple(c[x] for x in special), d)
        for a, b, c, d in sigs
    }) == 192

    hist = Counter()
    quotient_cells = 0
    lex_relevant_sets = 0
    sentence_relevant_sets = 0
    combined_relevant_sets = 0
    neutral = (("ALL_OTHER", False, {x: False for x in special}, 0),)

    for ids_tuple in id_sets:
        ids = set(ids_tuple)
        lex_relevant = FORB in ids and (NTH in ids or END in ids)
        if lex_relevant:
            lex_relevant_sets += 1
            lex_rows = sigs
        else:
            lex_rows = neutral
        sentence_rows = ("LESS_THAN_ONE", "LESS_THAN_GE_TWO", "AT_LEAST") if SENT in ids else ("ABSENT",)
        if SENT in ids:
            sentence_relevant_sets += 1
        if lex_relevant and SENT in ids:
            combined_relevant_sets += 1

        for nth_category, nth_forbidden, bits, end_index in lex_rows:
            end_hit = False
            if END in ids and FORB in ids:
                end_hit = any(
                    bits[word] and word in end_word_sets[end_index]
                    for word in special
                )
            lexical_loss = int(
                FORB in ids
                and ((NTH in ids and nth_forbidden) or end_hit)
            )
            for sentence_class in sentence_rows:
                sentence_loss = int(sentence_class == "LESS_THAN_ONE")
                loss = lexical_loss + sentence_loss
                assert loss <= 2
                quotient_cells += 1
                hist[loss] += 1

    assert quotient_cells == 53068
    assert dict(hist) == {0: 15503, 1: 31499, 2: 6066}
    assert (lex_relevant_sets, sentence_relevant_sets, combined_relevant_sets) == (172, 285, 49)

    mandatory_word_budget = sum((1, 1, 15, 5, 20, 5, 3, 8, 2))
    assert mandatory_word_budget == 60
    assert mandatory_word_budget < instructions._NUM_WORDS_LOWER_LIMIT
    assert (instructions._NUM_WORDS_UPPER_LIMIT - instructions._NUM_WORDS_LOWER_LIMIT + 1) * 2 == 802

    repeat = instructions.RepeatPromptThenAnswer(REPEAT)
    probe = "Ω exact visible prompt?\nsecond line"
    repeat.build_description(prompt_to_repeat=probe)
    assert repeat.check_following(probe + "\n<<9000001>>")

    return {
        "status": "PASS__INDEPENDENT_FULL_GENERATOR_POINTWISE_OPTIMUM_QUOTIENT",
        "compatible_id_sets": len(id_sets),
        "public_word_count": len(words),
        "lexical_signatures": len(sigs),
        "quotient_cells": quotient_cells,
        "loss_histogram": {str(k): v for k, v in sorted(hist.items())},
        "lexical_relevant_instruction_sets": lex_relevant_sets,
        "sentence_relevant_instruction_sets": sentence_relevant_sets,
        "combined_relevant_instruction_sets": combined_relevant_sets,
        "repeat_prompt_id_sets": len(repeat_sets),
        "json_id_sets": len(json_sets),
        "two_response_id_sets": len(two_sets),
        "mandatory_word_budget_upper_bound": mandatory_word_budget,
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
    }


def main() -> int:
    actual = {
        name: git_blob_sha(RUNTIME / name)
        for name in EXPECTED_BLOBS
    }
    mismatches = {
        name: {"expected": EXPECTED_BLOBS[name], "actual": actual[name]}
        for name in EXPECTED_BLOBS
        if actual[name] != EXPECTED_BLOBS[name]
    }
    if mismatches:
        write({
            "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL__SUBJECT_BLOB_MISMATCH",
            "mismatches": mismatches,
        })
        raise SystemExit("SUBJECT_BLOB_MISMATCH")

    sys.path.insert(0, str(SUBJECT))
    try:
        from canonical.runtime import (
            livebench_legacy15_sentence_wrapper_closure_v1 as closure,
        )
        result = closure.audit("/tmp/LiveBench")
    except Exception as exc:
        payload = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL__VERIFIER_EXCEPTION",
            "subject_blobs": actual,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }
        write(payload)
        raise

    quotient_proof_blob = git_blob_sha(QUOTIENT_PROOF)
    assert quotient_proof_blob == QUOTIENT_PROOF_BLOB, quotient_proof_blob
    quotient = independent_quotient_audit()

    passed = (
        result.get("status")
        == "PASS__2880_SENTENCE_WRAPPER_CASES_EXACT_POINTWISE_CLOSED"
        and result.get("failure_count") == 0
        and result.get("coverage", {}).get("cases") == 2880
        and result.get("coverage", {}).get("pointwise_exact_max_match") == 2880
        and quotient.get("status")
        == "PASS__INDEPENDENT_FULL_GENERATOR_POINTWISE_OPTIMUM_QUOTIENT"
        and quotient.get("quotient_cells") == 53068
        and quotient.get("loss_histogram") == {"0": 15503, "1": 31499, "2": 6066}
    )
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__INDEPENDENT_2880_SENTENCE_WRAPPER_POINTWISE_CLOSURE"
            if passed
            else "FAIL__INDEPENDENT_SENTENCE_WRAPPER_COUNTEREXAMPLE"
        ),
        "subject_blobs": actual,
        "quotient_proof_blob": quotient_proof_blob,
        "exact_result": result,
        "independent_full_generator_quotient": quotient,
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }
    write(receipt)
    print(json.dumps({
        "status": receipt["status"],
        "closure_status": result.get("status"),
        "coverage": result.get("coverage"),
        "failure_count": result.get("failure_count"),
        "quotient_status": quotient.get("status"),
        "quotient_cells": quotient.get("quotient_cells"),
        "quotient_loss_histogram": quotient.get("loss_histogram"),
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
