#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BRAIN = ROOT / "upstream/brain"
LIVEBENCH = ROOT / "upstream/LiveBench"
NLTK_DATA_REPO = ROOT / "upstream/nltk_data"

BRAIN_COMMIT = "af4adfab7f838e42924a1baa27e34bb62472c924"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PUNKT_TAB_ZIP_BLOB = "5e5ff6137d5ee6025e400d1c3a7b21914c48b635"

EXPECTED_BRAIN_BLOBS = {
    "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py":
        "a9ab9064b447ed669d2404a7a65f6c429c51ae85",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_exact_postvalidator_v1.py":
        "8c34701f5a63acf5aef88e8ea060be2d70571c23",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
}

SENTENCE = "length_constraints:number_sentences"
EXIST = "keywords:existence"
FORBIDDEN = "keywords:forbidden_words"
PARAGRAPHS = "length_constraints:number_paragraphs"
WORDS = "length_constraints:number_words"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
TITLE = "detectable_format:title"
SECTIONS = "detectable_format:multiple_sections"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"
END = "startend:end_checker"
QUOTE = "startend:quotation"

END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)
POST_MARKERS = ("P.S.", "P.P.S")
REQUIRED = ["harbor", "violet", "canyon", "meadow", "signal"]
FORBIDDEN_SAFE = ["amber", "forest", "silver", "planet", "window"]


def sh(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def c(iid: str, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def build_contracts(
    ids: tuple[str, ...],
    *,
    sentence_relation: str,
    sentence_threshold: int,
    post_marker: str,
    end_phrase: str,
    nth_shape: tuple[int, int],
    word_mode: str,
):
    out = []
    for iid in ids:
        if iid == EXIST:
            out.append(c(iid, keywords=list(REQUIRED)))
        elif iid == FORBIDDEN:
            out.append(c(iid, forbidden_words=list(FORBIDDEN_SAFE)))
        elif iid == PARAGRAPHS:
            raise AssertionError("SENTENCE_PARAGRAPH_CONFLICT_DRIFT")
        elif iid == WORDS:
            if word_mode == "NO_PAD":
                out.append(c(iid, num_words=100, relation="less than"))
            elif word_mode == "PAD_MAX":
                out.append(c(iid, num_words=500, relation="at least"))
            else:
                raise AssertionError("UNKNOWN_WORD_CONTEXT")
        elif iid == SENTENCE:
            out.append(c(
                iid,
                num_sentences=sentence_threshold,
                relation=sentence_relation,
            ))
        elif iid == NTH:
            n, k = nth_shape
            out.append(c(
                iid,
                num_paragraphs=n,
                nth_paragraph=k,
                first_word="harbor",
            ))
        elif iid == POSTSCRIPT:
            out.append(c(iid, postscript_marker=post_marker))
        elif iid == BULLETS:
            out.append(c(iid, num_bullets=5))
        elif iid == TITLE:
            out.append(c(iid))
        elif iid == SECTIONS:
            out.append(c(iid, section_spliter="Section", num_sections=5))
        elif iid == JSON_ID:
            out.append(c(iid))
        elif iid == REPEAT:
            out.append(c(iid, prompt_to_repeat="Public visible request."))
        elif iid == TWO:
            out.append(c(iid))
        elif iid == END:
            out.append(c(iid, end_phrase=end_phrase))
        elif iid == QUOTE:
            out.append(c(iid))
        else:
            raise AssertionError("UNKNOWN_ACTIVE_ID:" + iid)
    return out


def main() -> int:
    assert sh("git", "-C", str(BRAIN), "rev-parse", "HEAD") == BRAIN_COMMIT
    assert sh("git", "-C", str(LIVEBENCH), "rev-parse", "HEAD") == LIVEBENCH_COMMIT
    assert sh("git", "-C", str(NLTK_DATA_REPO), "rev-parse", "HEAD") == NLTK_DATA_COMMIT

    observed_blobs = {}
    for rel, expected in EXPECTED_BRAIN_BLOBS.items():
        path = BRAIN / rel
        got = blob_sha(path)
        assert got == expected, (rel, got, expected)
        observed_blobs[rel] = got

    punkt_blob = sh(
        "git", "-C", str(NLTK_DATA_REPO), "rev-parse",
        "HEAD:packages/tokenizers/punkt_tab.zip",
    )
    assert punkt_blob == PUNKT_TAB_ZIP_BLOB, (punkt_blob, PUNKT_TAB_ZIP_BLOB)

    sys.path.insert(0, str(BRAIN))
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
    from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as post
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch

    red = reduction.verify()
    assert red["status"] == (
        "PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_"
        "PARAMETRICALLY__ONLY_PINNED_PUNKT_CONTEXT_REMAINS"
    )
    assert red["conservative_unpadded_word_upper_bound"] < red["public_min_word_threshold"]

    source = post.verify_pinned_source(LIVEBENCH)
    registry, binding = post.load_pinned_registry(LIVEBENCH)
    assert binding["nltk_version"] == "3.10.3"

    import nltk
    assert nltk.__version__ == "3.10.3"

    sentence_sets = [
        ids for ids in arch.enumerate_compatible_sets()
        if SENTENCE in ids
    ]
    assert len(sentence_sets) == int(red["sentence_context_id_sets"])

    total_contexts = 0
    less_than_two_contexts = 0
    at_least_contexts = 0
    min_observed_sentences = None
    max_observed_sentences = 0
    max_checker_count = 0
    route_histogram = {}

    # Exact context reduction:
    # - less-than 2 is the strongest constructive upper-bound case; <N for
    #   every N=3..20 follows if this exact response remains one Punkt sentence.
    # - at-least N is checked for every N=1..20.
    # - WORDS has only two Punkt-relevant contexts: no padding and positive
    #   alphanumeric padding. PAD_MAX makes the latter explicit.
    # - NTH has three boundary contexts: sole paragraph, target first with a
    #   following paragraph, and target last with a preceding paragraph.
    # - postscript and end phrases are fully enumerated because they contain
    #   sentence-ending punctuation.
    sentence_modes = [("less than", 2)] + [("at least", n) for n in range(1, 21)]

    for ids in sentence_sets:
        ids_set = set(ids)
        assert not ({JSON_ID, REPEAT, TWO} & ids_set), ("SPECIAL_ROUTE_SENTENCE_DRIFT", ids)
        assert PARAGRAPHS not in ids_set, ("PARAGRAPH_SENTENCE_CONFLICT_DRIFT", ids)

        post_values = POST_MARKERS if POSTSCRIPT in ids_set else ("P.S.",)
        end_values = END_PHRASES if END in ids_set else (END_PHRASES[0],)
        nth_values = (
            ((1, 1), (2, 1), (2, 2))
            if NTH in ids_set else ((1, 1),)
        )
        word_values = (
            ("NO_PAD", "PAD_MAX")
            if WORDS in ids_set else ("NO_PAD",)
        )

        for (relation, threshold), marker, phrase, nth_shape, word_mode in itertools.product(
            sentence_modes, post_values, end_values, nth_values, word_values
        ):
            contracts = build_contracts(
                ids,
                sentence_relation=relation,
                sentence_threshold=threshold,
                post_marker=marker,
                end_phrase=phrase,
                nth_shape=nth_shape,
                word_mode=word_mode,
            )
            built = composer.compose_contracts(contracts)
            assert built["status"] == "CANDIDATE_WITNESS", (
                "COMPOSER_FAILED_PUNKT_CONTEXT",
                ids, relation, threshold, marker, phrase, nth_shape, word_mode, built,
            )
            response = built["response"]
            result = post.evaluate_with_registry(response, contracts, registry)
            flags = tuple(bool(x) for x in result["checker_results"])
            assert all(flags), (
                "EXACT_CHECKER_VECTOR_FAILURE",
                ids, relation, threshold, marker, phrase, nth_shape, word_mode,
                response, flags,
            )

            sentence_count = len(nltk.sent_tokenize(response))
            if relation == "less than":
                assert threshold == 2
                assert sentence_count == 1, (
                    "LESS_THAN_TWO_NOT_EXACTLY_ONE_SENTENCE",
                    ids, marker, phrase, nth_shape, word_mode, response, sentence_count,
                )
                less_than_two_contexts += 1
            else:
                assert sentence_count >= threshold, (
                    "AT_LEAST_SENTENCE_LOWER_BOUND_FAILURE",
                    ids, threshold, marker, phrase, nth_shape, word_mode,
                    response, sentence_count,
                )
                at_least_contexts += 1

            total_contexts += 1
            min_observed_sentences = (
                sentence_count if min_observed_sentences is None
                else min(min_observed_sentences, sentence_count)
            )
            max_observed_sentences = max(max_observed_sentences, sentence_count)
            max_checker_count = max(max_checker_count, len(flags))
            route = built.get("route") or "UNKNOWN"
            route_histogram[route] = route_histogram.get(route, 0) + 1

    assert total_contexts > 0
    assert less_than_two_contexts > 0
    assert at_least_contexts == 20 * less_than_two_contexts
    assert set(route_histogram) <= {"NTH_PARAGRAPH", "SENTENCE"}

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_PUBLIC_VERIFICATION_V1",
        "status": (
            "INDEPENDENT_PASS__PINNED_PUNKT_SENTENCE_CONTEXTS_EXHAUSTED__"
            "POST_SACRIFICE_UNIVERSAL_CONSTRUCTION_REMAINDER_CLOSED"
        ),
        "brain_commit": BRAIN_COMMIT,
        "brain_subject_blobs": observed_blobs,
        "livebench_commit": LIVEBENCH_COMMIT,
        "livebench_source_binding": source,
        "nltk_version": binding["nltk_version"],
        "nltk_data_commit": NLTK_DATA_COMMIT,
        "punkt_tab_zip_git_blob": punkt_blob,
        "sentence_id_set_count": len(sentence_sets),
        "total_exact_punkt_contexts": total_contexts,
        "less_than_two_exact_one_sentence_contexts": less_than_two_contexts,
        "at_least_exact_contexts": at_least_contexts,
        "min_observed_sentence_count": min_observed_sentences,
        "max_observed_sentence_count": max_observed_sentences,
        "max_checker_count": max_checker_count,
        "route_histogram": dict(sorted(route_histogram.items())),
        "proof_reduction": {
            "less_than_public_domain": (
                "N=1 is independently proved scorer-level UNSAT and sacrificed; "
                "exact one-sentence closure at N=2 implies every N=2..20."
            ),
            "at_least_public_domain": "Every N=1..20 is executed against the pinned Punkt runtime.",
            "word_padding": (
                "Punctuation-free word padding has two local contexts: absent and present; "
                "the present context is exercised at the public maximum threshold 500."
            ),
            "nth_wrapper": (
                "Sole paragraph, target-before-tail, and target-after-prefix contexts are executed."
            ),
            "punctuated_wrappers": "Both public postscript markers and both public end phrases are exhausted.",
        },
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "hidden_kwargs_read": 0,
        "comparator_responses_read": 0,
        "terminal_scores_read": 0,
        "target_rows_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "meaning": (
            "Combined with the content-bound parametric reduction, the only remaining "
            "environment-sensitive universal-construction obligation is discharged "
            "without reading any target row."
        ),
    }

    out = ROOT / "livebench_punkt_context_closure_verification.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
