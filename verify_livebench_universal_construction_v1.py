#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
NEW = ROOT / "subject/livebench_universal_construction_v1"
OLD = ROOT / "subject/livebench_composer_v2_20261005"
LIVE = pathlib.Path("/tmp/LiveBench")

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PUBLIC_BLOBS = {
    "livebench/if_runner/instruction_following_eval/instructions.py":
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench/if_runner/instruction_following_eval/instructions_registry.py":
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "livebench/if_runner/instruction_following_eval/instructions_util.py":
        "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}
SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "09a5d7810fd46713aaf06cf1d204fe140d1d8045",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":
        "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_universal_construction_v1.py":
        "f649eb5f50698775a4f7595e67235f0bc919fc4d",
}
OLD_PLANNER = OLD / "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
OLD_PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def exact_checker(registry, contract):
    iid = contract["instruction_id"]
    checker = registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(**dict(contract.get("slots") or {}))
    return checker


def fillers(words, exclude, n=4):
    ex = {str(x).lower() for x in exclude}
    out = []
    for w in words:
        if w.lower() not in ex:
            out.append(w)
            ex.add(w.lower())
        if len(out) == n:
            return out
    raise AssertionError("NOT_ENOUGH_FILLERS")


def main() -> int:
    for rel, expected in SUBJECT_BLOBS.items():
        got = hash_object(NEW / rel)
        assert got == expected, (rel, got, expected)
    assert hash_object(OLD_PLANNER) == OLD_PLANNER_BLOB

    assert run(
        ["git", "-C", str(LIVE), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip() == LIVEBENCH_COMMIT
    for rel, expected in PUBLIC_BLOBS.items():
        got = run(
            ["git", "-C", str(LIVE), "rev-parse", "HEAD:" + rel],
            capture_output=True,
        ).stdout.strip()
        assert got == expected, (rel, got, expected)

    sys.path.insert(0, str(NEW))
    sys.path.insert(1, str(OLD))
    sys.path.insert(0, str(LIVE / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_universal_construction_v1 as proof
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from instruction_following_eval import instructions_registry, instructions_util

    result = proof.verify()
    assert result["status"].startswith(
        "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCTION"
    )
    assert result["structural_id_sets"] == 928
    assert result["pointwise_loss_classification_cases"] == 928 * 192 * 2
    assert result["minimum_word_safety_margin"] == 52
    assert result["acceptance_credit"] is False

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
    lower = {w.lower() for w in words}

    end_phrases = (
        "Any other questions?",
        "Is there anything else I can help with?",
    )
    end_intersections = {
        phrase: sorted(
            set(re.findall(r"[A-Za-z]+", phrase.lower())) & lower
        )
        for phrase in end_phrases
    }
    assert end_intersections == {
        "Any other questions?": ["other"],
        "Is there anything else I can help with?": ["anything", "can", "help"],
    }
    assert ({x for x in ("section", "p", "s") if x in lower}) == {"section"}
    assert proof.SCAFFOLD_PUBLIC_WORD_HAZARDS == {
        "section", "other", "anything", "can", "help"
    }

    exact_counts = {
        "word_identity_shield": 0,
        "section_boundary_shield": 0,
        "postscript_no_public_token_collision": 0,
        "end_phrase_collision_classification": 0,
        "repeat_prefix": 0,
    }

    for w in words:
        other4 = fillers(words, {w}, 4)

        # Exact existence+forbidden checker semantics for every public identity.
        response = "9000" + w + "0009"
        exist = exact_checker(
            instructions_registry,
            {
                "instruction_id": comp.EXIST,
                "slots": {"keywords": [w] + other4},
            },
        )
        # Add the four remaining required words under the same word-character
        # shield so all five existence requirements are exact.
        response = "9000" + "0".join([w] + other4) + "0009"
        forbid = exact_checker(
            instructions_registry,
            {
                "instruction_id": comp.FORBIDDEN,
                "slots": {"forbidden_words": [w] + other4},
            },
        )
        assert exist.check_following(response)
        assert forbid.check_following(response)
        exact_counts["word_identity_shield"] += 1

        # Section is the only public word introduced by the section scaffold.
        # 9-prefix preserves SectionChecker's suffix regex and destroys the
        # whole-word boundary for the one hazardous identity.
        section_response = "9Section 1\n90000011"
        section = exact_checker(
            instructions_registry,
            {
                "instruction_id": comp.SECTIONS,
                "slots": {"section_spliter": "Section", "num_sections": 1},
            },
        )
        forbid_one = exact_checker(
            instructions_registry,
            {
                "instruction_id": comp.FORBIDDEN,
                "slots": {"forbidden_words": [w] + other4},
            },
        )
        assert section.check_following(section_response)
        assert forbid_one.check_following(section_response)
        exact_counts["section_boundary_shield"] += 1

        # Public WORD_LIST contains neither one-letter p nor s, so both public
        # postscript markers introduce no generated forbidden-word collision.
        for marker, response in (("P.S.", "9000001\nP.S.+"),
                                 ("P.P.S", "9000001\nP.P.S")):
            post = exact_checker(
                instructions_registry,
                {
                    "instruction_id": comp.POSTSCRIPT,
                    "slots": {"postscript_marker": marker},
                },
            )
            assert post.check_following(response)
            assert forbid_one.check_following(response)
            exact_counts["postscript_no_public_token_collision"] += 1

        # Independently recover the exact end/forbidden collision truth table.
        for phrase in end_phrases:
            end = exact_checker(
                instructions_registry,
                {
                    "instruction_id": comp.END,
                    "slots": {"end_phrase": phrase},
                },
            )
            assert end.check_following(phrase)
            got_forbidden_pass = forbid_one.check_following(phrase)
            expected_forbidden_pass = w.lower() not in set(
                re.findall(r"[A-Za-z]+", phrase.lower())
            )
            assert got_forbidden_pass is expected_forbidden_pass
            exact_counts["end_phrase_collision_classification"] += 1

    # Arbitrary repeat text is not a finite slot domain. The exact checker uses
    # strip/lower/startswith, so the proof is algebraic; adversarial strings
    # exercise whitespace, newlines, Unicode, and checker-looking syntax.
    repeat_samples = (
        "Public visible request.",
        "  leading and trailing  ",
        "Line one\nLine two",
        "Ä Unicode ARTICLE text ?! ",
        "<<title-like>>\n***\n* prompt syntax",
    )
    for raw in repeat_samples:
        checker = exact_checker(
            instructions_registry,
            {
                "instruction_id": comp.REPEAT,
                "slots": {"prompt_to_repeat": raw},
            },
        )
        response = raw.strip() + "\n9000001"
        assert checker.check_following(response)
        exact_counts["repeat_prefix"] += 1

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_CONSTRUCTION_INDEPENDENT_V1",
        "status": (
            "PASS__SUBJECT_REDUCTION_RECOMPUTED__PINNED_PUBLIC_CHECKERS_BOUND__"
            "ALL_1525_LEXICAL_IDENTITIES_RECHECKED"
        ),
        "subject_blobs": SUBJECT_BLOBS,
        "old_planner_blob": OLD_PLANNER_BLOB,
        "public_blobs": PUBLIC_BLOBS,
        "word_list_count": len(words),
        "word_list_unique": len(set(words)),
        "end_phrase_word_list_intersections": end_intersections,
        "exact_checker_counts": exact_counts,
        "structural_id_sets": result["structural_id_sets"],
        "pointwise_loss_classification_cases":
            result["pointwise_loss_classification_cases"],
        "minimum_word_safety_margin": result["minimum_word_safety_margin"],
        "deleted_requirements": result["deleted_requirements"],
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_responses_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_BIND_THE_ACCEPTED_LIVEBENCH_IF_GE_65_7_SCOPE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    pathlib.Path("livebench_universal_construction_v1_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
