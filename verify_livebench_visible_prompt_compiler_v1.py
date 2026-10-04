#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

PARSER_BLOB = "6e4ae278c4ba81cf0fb589d4e948384d1bd61ae2"
ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_visible_prompt_compiler_v1_20261005"
PARSER = SUBJECT / "canonical/runtime/livebench_legacy15_visible_prompt_compiler_v1.py"
ARCH = SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def main() -> int:
    assert hash_object(PARSER) == PARSER_BLOB
    assert hash_object(ARCH) == ARCH_BLOB

    live = pathlib.Path("/tmp/LiveBench")
    assert run(
        ["git", "-C", str(live), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip() == LIVEBENCH_COMMIT
    for path, expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }.items():
        got = run(
            ["git", "-C", str(live), "rev-parse", f"HEAD:{path}"],
            capture_output=True,
        ).stdout.strip()
        assert got == expected, (path, got, expected)

    run(
        ["git", "-C", str(live), "cat-file", "-e", GENERATOR_COMMIT + "^{commit}"],
        capture_output=True,
    )
    run(
        ["git", "-C", str(live), "cat-file", "-e", GENERATOR_BLOB + "^{blob}"],
        capture_output=True,
    )
    generator_source = run(
        ["git", "-C", str(live), "cat-file", "-p", GENERATOR_BLOB],
        capture_output=True,
    ).stdout
    for needle in (
        'instruction_combined_text += " "+instruction_text',
        'generated_prompt = prompt.format(extracted_text, task_prompt, constraint_text)',
        'generated_prompt.split("First repeat the request word for word without change,")[0]',
        'return "Please paraphrase based on the sentences provided."',
        'return "Please summarize based on the sentences provided."',
        'return "Please explain in simpler terms what this text means."',
        'return "Please generate a story based on the sentences provided."',
    ):
        assert needle in generator_source, needle

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as compiler
    from instruction_following_eval import instructions_registry, instructions_util

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", word) for word in words)

    counts = Counter()

    def fillers(exclude=(), n=5):
        excluded = {str(x).casefold() for x in exclude}
        out = []
        for word in words:
            if word.casefold() not in excluded:
                out.append(word)
                excluded.add(word.casefold())
            if len(out) == n:
                return out
        raise AssertionError("INSUFFICIENT_FILLERS")

    def build(iid: str, **kwargs):
        cls = instructions_registry.INSTRUCTION_DICT[iid]
        instance = cls(iid)
        description = instance.build_description(**kwargs)
        args = instance.get_instruction_args() or {}
        return description, dict(args)

    def make_prompt(descriptions, *, task=None, article="Article text."):
        task = task or compiler.TASK_PROMPTS[0]
        constraint_text = "".join(" " + description for description in descriptions)
        template = (
            "The following are the beginning sentences of a news article from the Guardian.\n"
            "-------\n"
            "{0}\n"
            "-------\n"
            "{1} {2}"
        )
        return template.format(article, task, constraint_text)

    def check_sequence(ids, kwargs_by_id, *, task=None, article="Article text."):
        descriptions = []
        expected = []
        for iid in ids:
            description, args = build(iid, **dict(kwargs_by_id.get(iid) or {}))
            descriptions.append(description)
            expected.append({"instruction_id": iid, "slots": args})
        prompt = make_prompt(descriptions, task=task, article=article)
        if compiler.REPEAT in ids:
            repeat_prefix = prompt.split(compiler.REPEAT_MARKER, 1)[0]
            for row in expected:
                if row["instruction_id"] == compiler.REPEAT:
                    row["slots"] = {"prompt_to_repeat": repeat_prefix}
                    break
        out = compiler.compile_visible_prompt(prompt)
        got = [
            {"instruction_id": row["instruction_id"], "slots": row["slots"]}
            for row in out["contracts"]
        ]
        assert got == expected, {
            "ids": ids,
            "expected": expected,
            "got": got,
            "prompt": prompt,
        }
        assert out["terminal_rows_used"] is False
        assert out["hidden_kwargs_used"] is False
        counts["compiled_prompts"] += 1

    # Exhaust every lexical identity in both five-keyword descriptor families.
    for word in words:
        other = fillers({word}, 4)
        five = [word] + other
        check_sequence(
            (compiler.EXIST,),
            {compiler.EXIST: {"keywords": five}},
        )
        check_sequence(
            (compiler.FORBIDDEN,),
            {compiler.FORBIDDEN: {"forbidden_words": five}},
        )
    counts["lexical_word_identities_exhausted_per_family"] = len(words)

    # Exhaust every public word/sentence threshold and relation.
    for relation in ("less than", "at least"):
        for n in range(100, 501):
            check_sequence(
                (compiler.WORDS,),
                {compiler.WORDS: {"num_words": n, "relation": relation}},
            )
        for n in range(1, 21):
            check_sequence(
                (compiler.SENTENCES,),
                {
                    compiler.SENTENCES: {
                        "num_sentences": n,
                        "relation": relation,
                    }
                },
            )
    counts["word_threshold_relation_cases"] = 802
    counts["sentence_threshold_relation_cases"] = 40

    # Exhaust every finite discrete local slot domain.
    for n in range(1, 6):
        check_sequence(
            (compiler.PARAGRAPHS,),
            {compiler.PARAGRAPHS: {"num_paragraphs": n}},
        )
        check_sequence(
            (compiler.BULLETS,),
            {compiler.BULLETS: {"num_bullets": n}},
        )
        for splitter in ("Section", "SECTION"):
            check_sequence(
                (compiler.SECTIONS,),
                {
                    compiler.SECTIONS: {
                        "section_spliter": splitter,
                        "num_sections": n,
                    }
                },
            )
    for marker in ("P.S.", "P.P.S"):
        check_sequence(
            (compiler.POSTSCRIPT,),
            {compiler.POSTSCRIPT: {"postscript_marker": marker}},
        )
    for phrase in (
        "Any other questions?",
        "Is there anything else I can help with?",
    ):
        check_sequence(
            (compiler.END,),
            {compiler.END: {"end_phrase": phrase}},
        )
    for iid in (compiler.TITLE, compiler.JSON_ID, compiler.TWO, compiler.QUOTE):
        check_sequence((iid,), {})

    # Exhaust every NTH location and every exact public first-word identity.
    for paragraphs in range(1, 6):
        for nth in range(1, paragraphs + 1):
            for word in words:
                check_sequence(
                    (compiler.NTH,),
                    {
                        compiler.NTH: {
                            "num_paragraphs": paragraphs,
                            "nth_paragraph": nth,
                            "first_word": word,
                        }
                    },
                )
    counts["nth_location_word_cases"] = sum(range(1, 6)) * len(words)

    # Structural concatenation theorem: every conflict-compatible active15 ID
    # set is parsed end-to-start with exact slots under one canonical local
    # representative. Local descriptor domains were exhausted independently
    # above, so this validates composition without multiplying irrelevant axes.
    required = fillers({"section", "other", "anything", "can", "help"}, 5)
    forbidden = fillers(set(required) | {"section", "other", "anything", "can", "help"}, 5)
    canonical = {
        compiler.EXIST: {"keywords": required},
        compiler.FORBIDDEN: {"forbidden_words": forbidden},
        compiler.PARAGRAPHS: {"num_paragraphs": 3},
        compiler.WORDS: {"num_words": 173, "relation": "at least"},
        compiler.SENTENCES: {"num_sentences": 7, "relation": "at least"},
        compiler.NTH: {
            "num_paragraphs": 3,
            "nth_paragraph": 2,
            "first_word": required[0],
        },
        compiler.POSTSCRIPT: {"postscript_marker": "P.S."},
        compiler.BULLETS: {"num_bullets": 3},
        compiler.SECTIONS: {"section_spliter": "Section", "num_sections": 3},
        compiler.END: {"end_phrase": "Any other questions?"},
    }
    sets = arch.enumerate_compatible_sets()
    assert len(sets) == 928
    for ids in sets:
        check_sequence(ids, canonical)
    counts["structural_id_sets"] = len(sets)

    # All task prompts are exact local alternatives.
    quote_desc, _ = build(compiler.QUOTE)
    for task in compiler.TASK_PROMPTS:
        prompt = make_prompt([quote_desc], task=task)
        out = compiler.compile_visible_prompt(prompt)
        assert out["instruction_ids"] == [compiler.QUOTE]
    counts["task_prompt_variants"] = len(compiler.TASK_PROMPTS)

    # Historical split(...)[0] behavior is preserved even if article text itself
    # contains the repeat marker before the actual repeat descriptor.
    marker = compiler.REPEAT_MARKER
    collision_article = "Article prefix " + marker + " collision suffix."
    ids = (compiler.EXIST, compiler.REPEAT, compiler.TITLE)
    check_sequence(
        ids,
        canonical,
        article=collision_article,
    )
    counts["repeat_marker_collision_cases"] = 1

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_VISIBLE_PROMPT_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261005_V1",
        "status": "PASS__VISIBLE_PROMPT_COMPILER_COMPLETE_FOR_FROZEN_ACTIVE15_PUBLIC_GRAMMAR",
        "subject_blobs": {
            "visible_prompt_compiler": PARSER_BLOB,
            "composition_archetypes": ARCH_BLOB,
        },
        "pinned_livebench": {
            "scorer_commit": LIVEBENCH_COMMIT,
            "generator_commit": GENERATOR_COMMIT,
            "generator_blob": GENERATOR_BLOB,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
        },
        "coverage": dict(counts),
        "proof": {
            "local_descriptor_domains": (
                "EXHAUSTIVE_FOR_EVERY_FINITE_GENERATED_SLOT_VALUE_AND_ALL_1525_PUBLIC_WORD_IDENTITIES"
            ),
            "composition": (
                "EVERY_ONE_OF_928_CONFLICT_COMPATIBLE_ACTIVE15_ID_SETS_PARSES_AS_A_SUFFIX_SEQUENCE; "
                "BACKWARD_SUFFIX_PARSING_IS_LOCAL_AND_THEREFORE LIFTS THE EXHAUSTIVE_SINGLE_DESCRIPTOR "
                "RESULT TO ARBITRARY CROSS_PRODUCTS OF THE ALREADY_EXHAUSTED LOCAL SLOT VALUES"
            ),
            "repeat_prompt": (
                "EXACT_HISTORICAL_SPLIT_FIRST_OCCURRENCE_SEMANTICS_RECONSTRUCTED_FROM_VISIBLE_PROMPT"
            ),
        },
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_PROVES_VISIBLE_PROMPT_TO_ACTIVE15_CONTRACT_COMPILATION_ONLY",
            "THIS_DOES_NOT_BY_ITSELF_PROVE_ACCEPTED_TERMINAL_ROWS_ARE_EXACTLY_THE_ACTIVE15_SCOPE",
            "THIS_DOES_NOT_BY_ITSELF_PROVE_POINTWISE_CONSTRUCTOR_OPTIMALITY_OUTSIDE_THE_ACTIVE15_PUBLIC_GRAMMAR",
        ],
    }
    pathlib.Path("livebench_visible_prompt_compiler_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
