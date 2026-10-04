#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

# Frozen source commitments. Changing any of these invalidates the theorem.\nEXPECTED = {
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
    paths = {name: base / name for name in EXPECTED}
    src = {}
    for name, path in paths.items():
        data = path.read_bytes()
        got = blob_sha(data)
        assert got == EXPECTED[name], (name, got, EXPECTED[name])
        src[name] = data.decode()

    words = literal_assignment(src["instructions_util.py"], "WORD_LIST")
    splitters = literal_assignment(src["instructions.py"], "_SECTION_SPLITER")
    endings = literal_assignment(src["instructions.py"], "_ENDING_OPTIONS")
    n_keywords = literal_assignment(src["instructions.py"], "_NUM_KEYWORDS")
    assert n_keywords == 5
    assert "section" in words and "help" in words
    assert set(splitters) == {"Section", "SECTION"}
    assert "Is there anything else I can help with?" in endings

    reg = src["instructions_registry.py"]
    # Identity compatibility premises. The pinned registry gives forbidden_words
    # only a self-conflict; multiple_sections and end_checker do not list it.
    assert '_KEYWORD + "forbidden_words": {_KEYWORD + "forbidden_words"}' in reg
    multi = reg.split('+ "multiple_sections": {', 1)[1].split("},", 1)[0]
    end = reg.split('_STARTEND + "end_checker": {_STARTEND + "end_checker"}', 1)
    assert '_KEYWORD + "forbidden_words"' not in multi
    assert len(end) == 2

    ins = src["instructions.py"]
    # Exact checker semantic premises.
    assert 're.search(r"\\b" + word + r"\\b", value, flags=re.IGNORECASE)' in ins
    assert 'section_splitter_patten = r"\\s?" + self._section_spliter  + r"\\s?\\d+\\s?"' in ins
    assert 'return num_sections >= self._num_sections' in ins
    assert 'return value.endswith(self._end_phrase)' in ins

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_UNIVERSALITY_REFUTATION_PUBLIC_RUNNER_V1",
        "status": "PASS__PUBLIC_SOURCE_FORMAL_COUNTEREXAMPLE_PREMISES_VERIFIED",
        "terminal_rows_read": 0,
        "terminal_instruction_ids_read": 0,
        "terminal_kwargs_read": 0,
        "source_blobs": EXPECTED,
        "keyword_pool_size": len(words),
        "keyword_pool_unique_count": len(set(words)),
        "counterexamples": [
            {
                "ids": ["keywords:forbidden_words", "detectable_format:multiple_sections"],
                "reachable_kwargs": {"forbidden_words_contains": "section", "section_spliter": "Section"},
                "conclusion": "UNSAT__SECTION_CHECKER_REQUIRES_WHOLE_WORD_SECTION_WHILE_FORBIDDEN_WORDS_REJECTS_IT",
            },
            {
                "ids": ["keywords:forbidden_words", "startend:end_checker"],
                "reachable_kwargs": {"forbidden_words_contains": "help", "end_phrase": "Is there anything else I can help with?"},
                "conclusion": "UNSAT__END_CHECKER_REQUIRES_WHOLE_WORD_HELP_WHILE_FORBIDDEN_WORDS_REJECTS_IT",
            },
        ],
        "theorem": "UNIVERSAL_ALL_GENERATOR_KWARGS_CONSTRUCTIVE_WITNESS_DOES_NOT_EXIST",
        "acceptance_credit": False,
    }
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
