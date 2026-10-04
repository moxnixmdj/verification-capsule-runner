#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
}

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def literal_assignment(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(("ASSIGNMENT_NOT_FOUND", name))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    base = Path(a.livebench_root) / "livebench" / "if_runner" / "instruction_following_eval"
    src = {}
    for name, expected in EXPECTED.items():
        data = (base / name).read_bytes()
        got = blob_sha(data)
        assert got == expected, (name, got, expected)
        src[name] = data.decode()

    words = literal_assignment(src["instructions_util.py"], "WORD_LIST")
    endings = literal_assignment(src["instructions.py"], "_ENDING_OPTIONS")
    n_keywords = literal_assignment(src["instructions.py"], "_NUM_KEYWORDS")
    assert n_keywords == 5
    assert len(words) == len(set(words)) == 1525
    assert "section" in words and "help" in words
    assert "Is there anything else I can help with?" in endings

    reg = src["instructions_registry.py"]
    # The two sound counterexample pairs are ID-compatible in the pinned graph.
    assert '_KEYWORD + "forbidden_words": {_KEYWORD + "forbidden_words"}' in reg
    nth_block = reg.split('_LENGTH + "nth_paragraph_first_word": {', 1)[1].split("},", 1)[0]
    assert '_KEYWORD + "forbidden_words"' not in nth_block
    assert '_STARTEND + "end_checker": {_STARTEND + "end_checker"}' in reg

    ins = src["instructions.py"]
    # Frozen checker semantic premises.
    assert 're.search(r"\\b" + word + r"\\b", value, flags=re.IGNORECASE)' in ins
    assert 'and first_word == self._first_word' in ins
    assert 'return value.endswith(self._end_phrase)' in ins

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_UNIVERSALITY_REFUTATION_PUBLIC_RUNNER_V2",
        "status": "PASS__PUBLIC_SOURCE_SOUND_COUNTEREXAMPLE_PREMISES_VERIFIED",
        "terminal_rows_read": 0,
        "terminal_instruction_ids_read": 0,
        "terminal_kwargs_read": 0,
        "source_blobs": EXPECTED,
        "keyword_pool_size": len(words),
        "keyword_pool_unique_count": len(set(words)),
        "retracted_v1_counterexample": {
            "ids": ["keywords:forbidden_words", "detectable_format:multiple_sections"],
            "old_claim": "UNSAT_WHEN_FORBIDDEN_CONTAINS_SECTION",
            "status": "RETRACTED",
            "reason": "SectionChecker permits zero whitespace before the numeric index; Section1 satisfies the section regex while destroying the trailing word boundary required by forbidden_words(section).",
        },
        "sound_counterexamples": [
            {
                "ids": ["keywords:forbidden_words", "length_constraints:nth_paragraph_first_word"],
                "reachable_kwargs": {
                    "forbidden_words_contains": "section",
                    "first_word": "section",
                },
                "conclusion": "UNSAT__NTH_FIRST_WORD_MUST_EQUAL_SECTION_AS_A_STANDALONE_FIRST_WORD_WHILE_FORBIDDEN_WORDS_REJECTS_WORD_BOUNDARY_SECTION",
            },
            {
                "ids": ["keywords:forbidden_words", "startend:end_checker"],
                "reachable_kwargs": {
                    "forbidden_words_contains": "help",
                    "end_phrase": "Is there anything else I can help with?",
                },
                "conclusion": "UNSAT__END_CHECKER_REQUIRES_WHOLE_WORD_HELP_WHILE_FORBIDDEN_WORDS_REJECTS_IT",
            },
        ],
        "theorem": "UNIVERSAL_FULL_SCORE_WITNESS_OVER_ALL_GENERATOR_ADMITTED_KWARGS_DOES_NOT_EXIST",
        "corrected_target": "POINTWISE_MAXIMALITY__FULL_SCORE_WHEN_SATISFIABLE__OTHERWISE_PROVE_REQUIRED_NEXT_CARDINALITY_SUBSETS_UNSAT",
        "acceptance_credit": False,
    }
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
