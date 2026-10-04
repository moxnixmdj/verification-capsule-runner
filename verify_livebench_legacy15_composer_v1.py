#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
CAPSULE_ROOT = Path("capsules/livebench_legacy15_composer_v1/brain").resolve()
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)

sys.path.insert(0, str(CAPSULE_ROOT))
sys.path.insert(0, "/tmp/livebench/livebench/if_runner")

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as shapes
from canonical.runtime import livebench_legacy15_special_composer_v1 as special
from canonical.runtime import livebench_legacy15_general_composer_v1 as general
from instruction_following_eval import instructions_registry

SAFE_KWARGS = {
    "keywords:existence": {
        "keywords": ["western", "signal", "potato", "agency", "world"],
    },
    "keywords:forbidden_words": {
        "forbidden_words": ["bad", "war", "sugar", "medicine", "film"],
    },
    "length_constraints:number_paragraphs": {"num_paragraphs": 3},
    "length_constraints:number_words": {"num_words": 120, "relation": "at least"},
    "length_constraints:number_sentences": {"num_sentences": 3, "relation": "at least"},
    "length_constraints:nth_paragraph_first_word": {
        "num_paragraphs": 3,
        "nth_paragraph": 2,
        "first_word": "western",
    },
    "detectable_content:postscript": {"postscript_marker": "P.S."},
    "detectable_format:number_bullet_lists": {"num_bullets": 3},
    "detectable_format:title": {},
    "detectable_format:multiple_sections": {
        "section_spliter": "Section",
        "num_sections": 3,
    },
    "detectable_format:json_format": {},
    "combination:repeat_prompt": {},
    "combination:two_responses": {},
    "startend:end_checker": {"end_phrase": "Any other questions?"},
    "startend:quotation": {},
}


def make_prompt(ids, overrides=None):
    overrides = overrides or {}
    descriptions = []
    kwargs_rows = []
    for iid in ids:
        kw = dict(SAFE_KWARGS[iid])
        kw.update(overrides.get(iid, {}))
        obj = instructions_registry.INSTRUCTION_DICT[iid](iid)
        desc = obj.build_description(**kw)
        descriptions.append(desc)
        kwargs_rows.append(kw)
    prompt = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Public synthetic article text used only for source-level verification.\n"
        "-------\n"
        "Please summarize based on the sentences provided. "
        + " ".join(descriptions)
    )
    for i, iid in enumerate(ids):
        if iid == "combination:repeat_prompt":
            kwargs_rows[i] = dict(kwargs_rows[i])
            kwargs_rows[i]["prompt_to_repeat"] = prompt.split(REPEAT_MARKER)[0]
    return prompt, kwargs_rows


def exact_check(ids, kwargs_rows, response):
    failures = []
    for iid, kw in zip(ids, kwargs_rows):
        obj = instructions_registry.INSTRUCTION_DICT[iid](iid)
        obj.build_description(**kw)
        try:
            ok = bool(obj.check_following(response))
        except Exception as exc:
            failures.append({
                "instruction_id": iid,
                "exception": type(exc).__name__,
                "detail": str(exc),
            })
            continue
        if not ok:
            failures.append({"instruction_id": iid, "check_following": False})
    return failures


def candidate_for(ids, prompt):
    special_ids = {
        "detectable_format:json_format",
        "combination:two_responses",
        "combination:repeat_prompt",
    }
    if set(ids) & special_ids:
        return special.compose_visible_prompt(prompt)
    return general.compose_visible_prompt(prompt)


def run_case(ids, overrides=None, expect_fail_closed=False):
    prompt, kwargs_rows = make_prompt(ids, overrides)
    out = candidate_for(ids, prompt)
    if expect_fail_closed:
        if out.get("status") != "FAIL_CLOSED":
            return {"error": "EXPECTED_FAIL_CLOSED", "out": out}
        return None
    if not str(out.get("status", "")).startswith("PASS_CANDIDATE_"):
        return {"error": "CANDIDATE_NOT_PASS", "out": out}
    response = out.get("response")
    failures = exact_check(ids, kwargs_rows, response)
    if failures:
        return {
            "error": "EXACT_CHECKER_FAILURE",
            "candidate_status": out.get("status"),
            "branch": out.get("branch") or out.get("archetype"),
            "instruction_ids": list(ids),
            "failures": failures,
            "response_prefix": response[:500] if isinstance(response, str) else None,
        }
    return None


def main():
    shape_receipt = shapes.verify()
    all_shapes = shapes.enumerate_compatible_sets()
    failures = []

    # Exhaust the entire historical identity-shape superset (size 1..5) at a
    # source-valid safe parameter point. This is 928 exact scorer executions at
    # the shape level, not terminal cases.
    for ids in all_shapes:
        failure = run_case(ids)
        if failure:
            failures.append({"kind": "SAFE_SHAPE_GRID", **failure})

    # Parameter-edge probes for the source ranges and interaction risks.
    probes = [
        (
            ("detectable_format:json_format", "keywords:existence", "keywords:forbidden_words"),
            {
                "keywords:existence": {"keywords": ["war", "signal", "potato", "agency", "world"]},
                "keywords:forbidden_words": {"forbidden_words": ["war", "bad", "sugar", "medicine", "film"]},
            },
            False,
            "JSON_REQUIRED_FORBIDDEN_OVERLAP",
        ),
        (
            ("combination:two_responses", "detectable_format:title", "keywords:existence", "keywords:forbidden_words"),
            {
                "keywords:existence": {"keywords": ["war", "signal", "potato", "agency", "world"]},
                "keywords:forbidden_words": {"forbidden_words": ["war", "bad", "sugar", "medicine", "film"]},
            },
            False,
            "TWO_REQUIRED_FORBIDDEN_OVERLAP",
        ),
        (
            ("combination:repeat_prompt", "detectable_format:title", "keywords:existence"),
            {},
            False,
            "REPEAT_FULL_PREFIX_RECOVERY",
        ),
        (
            ("length_constraints:number_paragraphs", "length_constraints:number_words", "startend:end_checker", "startend:quotation"),
            {"length_constraints:number_paragraphs": {"num_paragraphs": 5},
             "length_constraints:number_words": {"num_words": 500, "relation": "at least"},
             "startend:end_checker": {"end_phrase": "Is there anything else I can help with?"}},
            False,
            "STAR_PARAGRAPH_WORD500_END_QUOTE",
        ),
        (
            ("length_constraints:number_words", "detectable_format:number_bullet_lists", "startend:end_checker", "startend:quotation"),
            {"length_constraints:number_words": {"num_words": 100, "relation": "less than"},
             "detectable_format:number_bullet_lists": {"num_bullets": 5}},
            False,
            "WORD_LT100_BULLET_QUOTE_END",
        ),
        (
            ("length_constraints:nth_paragraph_first_word", "length_constraints:number_sentences", "length_constraints:number_words", "startend:end_checker", "startend:quotation"),
            {"length_constraints:nth_paragraph_first_word": {"num_paragraphs": 5, "nth_paragraph": 5, "first_word": "western"},
             "length_constraints:number_sentences": {"num_sentences": 20, "relation": "at least"},
             "length_constraints:number_words": {"num_words": 500, "relation": "at least"}},
            False,
            "NTH_SENTENCE20_WORD500_END_QUOTE",
        ),
        (
            ("length_constraints:number_sentences",),
            {"length_constraints:number_sentences": {"num_sentences": 1, "relation": "less than"}},
            False,
            "SENTENCE_LT1_EMPTY",
        ),
        (
            ("length_constraints:number_sentences", "startend:end_checker"),
            {"length_constraints:number_sentences": {"num_sentences": 2, "relation": "less than"}},
            False,
            "SENTENCE_LT2_END",
        ),
        (
            ("length_constraints:number_sentences", "detectable_content:postscript", "startend:end_checker"),
            {"length_constraints:number_sentences": {"num_sentences": 2, "relation": "less than"}},
            True,
            "SENTENCE_LT2_POSTSCRIPT_END_FAIL_CLOSED",
        ),
        (
            ("length_constraints:nth_paragraph_first_word", "length_constraints:number_sentences"),
            {"length_constraints:number_sentences": {"num_sentences": 3, "relation": "less than"}},
            True,
            "NTH_SENTENCE_LESS_FAIL_CLOSED",
        ),
        (
            ("detectable_format:multiple_sections", "keywords:forbidden_words"),
            {"keywords:forbidden_words": {"forbidden_words": ["section", "bad", "war", "sugar", "medicine"]}},
            True,
            "MANDATORY_SECTION_FORBIDDEN_FAIL_CLOSED",
        ),
    ]

    for ids, overrides, expect_fail, label in probes:
        failure = run_case(ids, overrides, expect_fail_closed=expect_fail)
        if failure:
            failures.append({"kind": "PARAMETER_PROBE", "label": label, **failure})

    receipt = {
        "schema": "LIVEBENCH_LEGACY15_COMPOSER_PUBLIC_EXACT_SOURCE_VERIFICATION_V1",
        "livebench_commit": LIVEBENCH_COMMIT,
        "active_identity_count": 15,
        "identity_shapes_executed": len(all_shapes),
        "shape_counts_by_size": shape_receipt["counts_by_size"],
        "archetype_counts": shape_receipt["counts_by_archetype"],
        "parameter_probe_count": len(probes),
        "failure_count": len(failures),
        "failures": failures[:50],
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "terminal_case_score_read": 0,
        "acceptance_credit": False,
        "status": "PASS" if not failures else "FAIL",
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
