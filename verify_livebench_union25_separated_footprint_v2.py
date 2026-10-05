#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
import string
import urllib.request
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
BRAIN_RUNTIME_BLOB = "3c11e8d0ca82c0d2768fe99e4df15f981431dc22"
BRAIN_TEST_BLOB = "3672439b834c0526ac8d856ed98a8597559b554e"

RAW_BASE = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/"
    + LIVEBENCH_COMMIT
    + "/livebench/if_runner/instruction_following_eval/"
)
OUT = Path("livebench_union25_separated_footprint_v2_receipt.json")


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def fetch(name: str, expected: str) -> str:
    with urllib.request.urlopen(RAW_BASE + name, timeout=30) as r:
        data = r.read()
    got = git_blob_sha(data)
    assert got == expected, (name, expected, got)
    return data.decode("utf-8")


def literal_assignment(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise AssertionError("MISSING_LITERAL_ASSIGNMENT:" + name)


def postscript_ok(value: str, marker: str) -> bool:
    value = value.lower()
    if marker == "P.P.S":
        pattern = r"\s*p\.\s?p\.\s?s.*$"
    elif marker == "P.S.":
        pattern = r"\s*p\.\s?s\..*$"
    else:
        raise AssertionError(marker)
    return bool(re.findall(pattern, value, flags=re.MULTILINE))


def section_ok(value: str, splitter: str, n: int) -> bool:
    pattern = r"\s?" + splitter + r"\s?\d+\s?"
    return len(re.split(pattern, value)) - 1 >= n


def end_ok(value: str, phrase: str) -> bool:
    return value.strip().strip('"').lower().endswith(phrase.strip().lower())


def witness(splitter: str, n: int, marker: str, ending: str) -> str:
    sections = "\n".join(f"{splitter} {i}\n9" for i in range(1, n + 1))
    # Same line after the marker is deliberate: it satisfies the exact
    # MULTILINE postscript regex while preserving the exact ending suffix.
    return sections + "\n" + marker + "+ " + ending


def structural_keyword_floor(keyword: str, splitter: str, n: int, marker: str, ending: str) -> int:
    return (
        len(re.findall(keyword, splitter, flags=re.IGNORECASE)) * n
        + len(re.findall(keyword, marker, flags=re.IGNORECASE))
        + len(re.findall(keyword, ending, flags=re.IGNORECASE))
    )


def structural_letter_floor(letter: str, splitter: str, n: int, marker: str, ending: str) -> int:
    letter = letter.lower()
    return (
        splitter.lower().count(letter) * n
        + marker.lower().count(letter)
        + ending.lower().count(letter)
    )


def main() -> int:
    instructions = fetch("instructions.py", INSTRUCTIONS_BLOB)
    util = fetch("instructions_util.py", UTIL_BLOB)

    splitters = tuple(literal_assignment(instructions, "_SECTION_SPLITER"))
    markers = tuple(literal_assignment(instructions, "_POSTSCRIPT_MARKER"))
    endings = tuple(literal_assignment(instructions, "_ENDING_OPTIONS"))
    words = tuple(literal_assignment(util, "WORD_LIST"))

    assert splitters == ("Section", "SECTION")
    assert markers == ("P.S.", "P.P.S")
    assert endings == (
        "Any other questions?",
        "Is there anything else I can help with?",
    )
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(w.isascii() and w.isalpha() for w in words)

    # Bind the exact source semantics this theorem relies on. The full blobs are
    # already content-addressed; these assertions prevent silently verifying a
    # different checker interpretation.
    required_source_fragments = (
        'section_splitter_patten = r"\\s?" + self._section_spliter  + r"\\s?\\d+\\s?"',
        "sections = re.split(section_splitter_patten, value)",
        'postscript_pattern = r"\\s*p\\.\\s?p\\.\\s?s.*$"',
        'postscript_pattern = r"\\s*p\\.\\s?s\\..*$"',
        "return value.endswith(self._end_phrase)",
        "actual_occurrences = len(re.findall(",
        "value = value.lower()",
        "letters = collections.Counter(value)",
    )
    for fragment in required_source_fragments:
        assert fragment in instructions, fragment

    # Fixed-family witness spans cannot alias one another.
    for ending in endings:
        low = ending.casefold()
        assert "section" not in low
        assert "p.s." not in low
        assert "p.p.s" not in low
    for marker in markers:
        assert "section" not in marker.casefold()
        assert all(ending.casefold() not in marker.casefold() for ending in endings)

    combos = 0
    letter_checks = 0
    keyword_checks = 0
    max_letter_gain_over_v1_max = 0
    strongest = None

    for splitter in splitters:
        for n in range(1, 6):
            for marker in markers:
                for ending in endings:
                    value = witness(splitter, n, marker, ending)
                    assert section_ok(value, splitter, n)
                    assert postscript_ok(value, marker)
                    assert end_ok(value, ending)
                    combos += 1

                    for letter in string.ascii_lowercase:
                        floor = structural_letter_floor(letter, splitter, n, marker, ending)
                        actual = value.lower().count(letter)
                        assert actual >= floor
                        component_max = max(
                            splitter.lower().count(letter) * n,
                            marker.lower().count(letter),
                            ending.lower().count(letter),
                        )
                        gain = floor - component_max
                        if gain > max_letter_gain_over_v1_max:
                            max_letter_gain_over_v1_max = gain
                            strongest = {
                                "splitter": splitter,
                                "num_sections": n,
                                "postscript_marker": marker,
                                "ending": ending,
                                "letter": letter,
                                "v1_max_floor": component_max,
                                "v2_separated_sum_floor": floor,
                            }
                        letter_checks += 1

                    for keyword in words:
                        floor = structural_keyword_floor(keyword, splitter, n, marker, ending)
                        actual = len(re.findall(keyword, value, flags=re.IGNORECASE))
                        assert actual >= floor, (keyword, splitter, n, marker, ending, floor, actual)
                        keyword_checks += 1

    # Regression witness highlighted by the canonical V2 tests.
    demo = structural_letter_floor(
        "s", "SECTION", 2, "P.S.", "Any other questions?"
    )
    assert demo == 5
    old_demo = max(
        "SECTION".lower().count("s") * 2,
        "P.S.".lower().count("s"),
        "Any other questions?".lower().count("s"),
    )
    assert old_demo == 2

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_UNION25_SEPARATED_FOOTPRINT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__PINNED_PUBLIC_SOURCE_PROVES_SEPARATED_STRUCTURAL_FLOORS_ADD",
        "livebench_commit": LIVEBENCH_COMMIT,
        "instructions_blob": INSTRUCTIONS_BLOB,
        "instructions_util_blob": UTIL_BLOB,
        "brain_subject_runtime_blob": BRAIN_RUNTIME_BLOB,
        "brain_subject_test_blob": BRAIN_TEST_BLOB,
        "public_word_count": len(words),
        "structural_combinations_verified": combos,
        "letter_target_checks": letter_checks,
        "keyword_target_checks": keyword_checks,
        "demo_v1_max_floor": old_demo,
        "demo_v2_separated_sum_floor": demo,
        "max_letter_floor_gain_over_v1_component_max": max_letter_gain_over_v1_max,
        "strongest_observed_letter_example": strongest,
        "proof_basis": [
            "PINNED_SECTION_RE_SPLIT_REQUIRES_NONOVERLAPPING_SECTION_MATCHES",
            "PINNED_POSTSCRIPT_REGEX_REQUIRES_FIXED_P_S_OR_P_P_S_MARKER",
            "PINNED_END_CHECKER_REQUIRES_FIXED_SUFFIX",
            "FIXED_CROSS_FAMILY_LITERALS_DO_NOT_ALIAS",
            "REGEX_AND_LETTER_OCCURRENCES_INTERNAL_TO_DISJOINT_MANDATORY_SPANS_ADD",
            "EXISTENCE_AND_NTH_FIRST_WORD_REMAIN_NONADDITIVE_MAX_ONLY",
        ],
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
