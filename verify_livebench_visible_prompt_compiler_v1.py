#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Mapping

COMPILER_BLOB = "6e4ae278c4ba81cf0fb589d4e948384d1bd61ae2"
ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
LIVE_DATA_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_visible_compiler_20261005"
COMPILER = SUBJECT / "canonical/runtime/livebench_legacy15_visible_prompt_compiler_v1.py"
ARCH = SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"

HEADER = (
    "The following are the beginning sentences of a news article from the Guardian.\n"
    "-------\n"
)
ARTICLE = "Public article sentence one. Public article sentence two."
MID = "\n-------\n"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def git_blob(repo: pathlib.Path, rel: str) -> str:
    return run(
        ["git", "-C", str(repo), "rev-parse", f"HEAD:{rel}"],
        capture_output=True,
    ).stdout.strip()


def norm(value):
    if isinstance(value, Mapping):
        return {str(k): norm(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [norm(x) for x in value]
    if hasattr(value, "item"):
        try:
            return norm(value.item())
        except Exception:
            pass
    return value


def canonical_slots(iid: str, slots: dict) -> dict:
    out = norm(slots)
    if iid in {"keywords:existence", "keywords:forbidden_words"}:
        key = "keywords" if iid == "keywords:existence" else "forbidden_words"
        out[key] = list(out[key])
    return out


def main() -> int:
    assert hash_object(COMPILER) == COMPILER_BLOB
    assert hash_object(ARCH) == ARCH_BLOB

    live = pathlib.Path("/tmp/LiveBenchGen")
    head = run(
        ["git", "-C", str(live), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip()
    assert head == GENERATOR_COMMIT
    assert git_blob(live, "livebench/if_runner/live_data.py") == LIVE_DATA_BLOB
    assert git_blob(
        live,
        "livebench/if_runner/instruction_following_eval/instructions.py",
    ) == INSTRUCTIONS_BLOB
    assert git_blob(
        live,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py",
    ) == REGISTRY_BLOB
    assert git_blob(
        live,
        "livebench/if_runner/instruction_following_eval/instructions_util.py",
    ) == UTIL_BLOB

    live_data_text = (
        live / "livebench/if_runner/live_data.py"
    ).read_text(encoding="utf-8")
    required_generator_semantics = (
        'instruction_combined_text += " "+instruction_text',
        'generated_prompt = prompt.format(extracted_text, task_prompt, constraint_text)',
        'generated_prompt.split("First repeat the request word for word without change,")[0]',
        'return "Please paraphrase based on the sentences provided."',
        'return "Please summarize based on the sentences provided."',
        'return "Please explain in simpler terms what this text means."',
        'return "Please generate a story based on the sentences provided."',
    )
    for needle in required_generator_semantics:
        assert needle in live_data_text, needle

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as compiler
    from instruction_following_eval import instructions_registry, instructions_util

    assert tuple(arch.ACTIVE_IDS) == tuple(compiler.archetypes.ACTIVE_IDS)
    assert set(arch.ACTIVE_IDS) <= set(instructions_registry.INSTRUCTION_DICT)

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", str(w)) for w in words)

    tasks = tuple(compiler.TASK_PROMPTS)
    assert tasks == (
        "Please paraphrase based on the sentences provided.",
        "Please summarize based on the sentences provided.",
        "Please explain in simpler terms what this text means.",
        "Please generate a story based on the sentences provided.",
    )

    def make_prompt(descriptions, *, task=tasks[0], article=ARTICLE):
        # Historical generator: prompt has one literal space before a constraint
        # string that itself starts with one space per descriptor.
        constraint_text = "".join(" " + d for d in descriptions)
        return HEADER + article + MID + task + " " + constraint_text

    def desc_args(iid: str, slots: dict | None = None):
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        if slots:
            desc = checker.build_description(**slots)
        else:
            desc = checker.build_description()
        args = checker.get_instruction_args()
        return str(desc), canonical_slots(iid, dict(args or {}))

    def compiled_expected(iid: str, desc: str, expected_slots: dict, *, task=tasks[0], article=ARTICLE):
        prompt = make_prompt([desc], task=task, article=article)
        got = compiler.compile_visible_prompt(prompt)
        assert got["instruction_ids"] == [iid]
        contract = got["contracts"][0]
        assert contract["instruction_id"] == iid
        if iid == compiler.REPEAT:
            expected = {
                "prompt_to_repeat": prompt.split(compiler.REPEAT_MARKER, 1)[0]
            }
        else:
            expected = canonical_slots(iid, expected_slots)
        assert canonical_slots(iid, contract["slots"]) == expected, (
            iid,
            contract["slots"],
            expected,
            desc,
        )
        return 1

    counts = {
        "single_descriptor_cases": 0,
        "keyword_identity_cases": 0,
        "nth_word_identity_position_cases": 0,
        "numeric_discrete_cases": 0,
        "task_prompt_cases": 0,
        "compatible_order_cases": 0,
    }

    # Exact fixed/no-argument families.
    for iid in (
        compiler.TITLE,
        compiler.JSON_ID,
        compiler.REPEAT,
        compiler.TWO,
        compiler.QUOTE,
    ):
        desc, args = desc_args(iid)
        counts["single_descriptor_cases"] += compiled_expected(iid, desc, args)

    # Exact small finite domains.
    for n in range(1, 6):
        for iid, slots in (
            (compiler.PARAGRAPHS, {"num_paragraphs": n}),
            (compiler.BULLETS, {"num_bullets": n}),
        ):
            desc, args = desc_args(iid, slots)
            counts["single_descriptor_cases"] += compiled_expected(iid, desc, args)
            counts["numeric_discrete_cases"] += 1

    for splitter in ("Section", "SECTION"):
        for n in range(1, 6):
            desc, args = desc_args(
                compiler.SECTIONS,
                {"section_spliter": splitter, "num_sections": n},
            )
            counts["single_descriptor_cases"] += compiled_expected(
                compiler.SECTIONS, desc, args
            )
            counts["numeric_discrete_cases"] += 1

    for marker in ("P.S.", "P.P.S"):
        desc, args = desc_args(
            compiler.POSTSCRIPT, {"postscript_marker": marker}
        )
        counts["single_descriptor_cases"] += compiled_expected(
            compiler.POSTSCRIPT, desc, args
        )
        counts["numeric_discrete_cases"] += 1

    for phrase in (
        "Any other questions?",
        "Is there anything else I can help with?",
    ):
        desc, args = desc_args(compiler.END, {"end_phrase": phrase})
        counts["single_descriptor_cases"] += compiled_expected(
            compiler.END, desc, args
        )
        counts["numeric_discrete_cases"] += 1

    for relation in ("less than", "at least"):
        for n in range(100, 501):
            desc, args = desc_args(
                compiler.WORDS,
                {"num_words": n, "relation": relation},
            )
            counts["single_descriptor_cases"] += compiled_expected(
                compiler.WORDS, desc, args
            )
            counts["numeric_discrete_cases"] += 1
        for n in range(1, 21):
            desc, args = desc_args(
                compiler.SENTENCES,
                {"num_sentences": n, "relation": relation},
            )
            counts["single_descriptor_cases"] += compiled_expected(
                compiler.SENTENCES, desc, args
            )
            counts["numeric_discrete_cases"] += 1

    # Every public lexical identity is exercised for both five-word list
    # families. The parser theorem is identity-independent once the pinned
    # source establishes ASCII alphabetic uniqueness.
    for index, word in enumerate(words):
        fillers = [x for x in words if x != word][:4]
        five = [word, *fillers]
        assert len(five) == 5 and len(set(five)) == 5
        for iid, key in (
            (compiler.EXIST, "keywords"),
            (compiler.FORBIDDEN, "forbidden_words"),
        ):
            desc, args = desc_args(iid, {key: five})
            counts["single_descriptor_cases"] += compiled_expected(iid, desc, args)
            counts["keyword_identity_cases"] += 1

    # NTH first-word identity can be any public WORD_LIST value; exhaust every
    # identity at every reachable paragraph/position pair.
    for word in words:
        for p in range(1, 6):
            for k in range(1, p + 1):
                desc, args = desc_args(
                    compiler.NTH,
                    {
                        "num_paragraphs": p,
                        "nth_paragraph": k,
                        "first_word": str(word).lower(),
                    },
                )
                counts["single_descriptor_cases"] += compiled_expected(
                    compiler.NTH, desc, args
                )
                counts["nth_word_identity_position_cases"] += 1

    # Every historical task-prompt variant feeds the same descriptor suffix.
    quote_desc, quote_args = desc_args(compiler.QUOTE)
    for task in tasks:
        counts["single_descriptor_cases"] += compiled_expected(
            compiler.QUOTE, quote_desc, quote_args, task=task
        )
        counts["task_prompt_cases"] += 1

    # The historical repeat implementation splits at the first visible marker,
    # including the pathological case where article content already contains it.
    collision_article = (
        "Article prefix "
        + compiler.REPEAT_MARKER
        + " collision before the generated descriptor."
    )
    repeat_desc, repeat_args = desc_args(compiler.REPEAT)
    compiled_expected(
        compiler.REPEAT,
        repeat_desc,
        repeat_args,
        article=collision_article,
    )

    # Representative descriptor/slot pair for each family, sourced from the
    # exact pinned checker implementation, never hand-written parser fixtures.
    safe = [str(x) for x in words[:12]]
    reps = {
        compiler.EXIST: {"keywords": safe[:5]},
        compiler.FORBIDDEN: {"forbidden_words": safe[5:10]},
        compiler.PARAGRAPHS: {"num_paragraphs": 3},
        compiler.WORDS: {"num_words": 300, "relation": "at least"},
        compiler.SENTENCES: {"num_sentences": 7, "relation": "at least"},
        compiler.NTH: {
            "num_paragraphs": 4,
            "nth_paragraph": 3,
            "first_word": safe[10].lower(),
        },
        compiler.POSTSCRIPT: {"postscript_marker": "P.P.S"},
        compiler.BULLETS: {"num_bullets": 4},
        compiler.TITLE: {},
        compiler.SECTIONS: {"section_spliter": "SECTION", "num_sections": 4},
        compiler.JSON_ID: {},
        compiler.REPEAT: {},
        compiler.TWO: {},
        compiler.END: {"end_phrase": "Any other questions?"},
        compiler.QUOTE: {},
    }
    descriptor_cache = {}
    args_cache = {}
    for iid in arch.ACTIVE_IDS:
        d, a = desc_args(iid, reps[iid])
        descriptor_cache[iid] = d
        args_cache[iid] = a

    compatible_sets = arch.enumerate_compatible_sets()
    assert len(compatible_sets) == 928

    # Order is semantically live because the historical generator converts a
    # deconflicted set back to list. Exhaust every permutation of every
    # conflict-compatible Active15 set up to the public five-instruction bound.
    for ids in compatible_sets:
        for order in itertools.permutations(ids):
            descriptions = [descriptor_cache[iid] for iid in order]
            prompt = make_prompt(descriptions)
            got = compiler.compile_visible_prompt(prompt)
            assert tuple(got["instruction_ids"]) == tuple(order)
            assert got["descriptor_count"] == len(order)
            assert len(got["contracts"]) == len(order)
            for iid, contract in zip(order, got["contracts"]):
                assert contract["instruction_id"] == iid
                if iid == compiler.REPEAT:
                    expected = {
                        "prompt_to_repeat": prompt.split(
                            compiler.REPEAT_MARKER, 1
                        )[0]
                    }
                else:
                    expected = canonical_slots(iid, args_cache[iid])
                assert canonical_slots(iid, contract["slots"]) == expected
            counts["compatible_order_cases"] += 1

    expected_order_cases = sum(
        1
        for ids in compatible_sets
        for _ in itertools.permutations(ids)
    )
    assert counts["compatible_order_cases"] == expected_order_cases

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_VISIBLE_PROMPT_COMPILER_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__EXACT_HISTORICAL_GENERATOR_DESCRIPTORS__"
            "ALL_ACTIVE15_PUBLIC_SLOT_DOMAINS__ALL_COMPATIBLE_ID_ORDERS__"
            "ZERO_TERMINAL_ROWS"
        ),
        "subject_blobs": {
            "visible_prompt_compiler": COMPILER_BLOB,
            "composition_archetypes": ARCH_BLOB,
        },
        "pinned_generator": {
            "commit": GENERATOR_COMMIT,
            "live_data_blob": LIVE_DATA_BLOB,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "public_word_list_count": len(words),
        },
        "coverage": counts,
        "compatible_id_set_count": len(compatible_sets),
        "all_public_task_prompts": len(tasks),
        "repeat_first_marker_collision_case": "PASS",
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "hidden_terminal_instruction_ids_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
    }
    pathlib.Path(
        "livebench_visible_prompt_compiler_v1_verification.json"
    ).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
