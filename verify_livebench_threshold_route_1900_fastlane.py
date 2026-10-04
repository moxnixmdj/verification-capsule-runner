#!/usr/bin/env python3
"""Independent fast-lane verifier for Brain PR #1900 minimal LiveBench proof.

Verifies exact carried subject blobs, executes the candidate tests in isolation,
and independently rechecks the exact public-source premises of the minimal
generator-admitted contradiction:

ForbiddenWords can draw five distinct WORD_LIST entries containing "help";
EndChecker can require "Is there anything else I can help with?"; the IDs are
conflict-compatible; exact semantics make simultaneous success impossible.

No terminal LiveBench rows, row metadata, responses, frequencies, or scores are read.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_threshold_route_1900"
LIVEBENCH = Path(os.environ.get("LIVEBENCH_ROOT", "/tmp/livebench"))

EXPECTED = {
    "livebench_generator_support_threshold_route_falsifier_v2.py": "5e6a6bf016ab2ba41c882981d1ab9e488f0d5f19",
    "test_livebench_generator_support_threshold_route_falsifier_v2.py": "a7676edf8cb672a8fa8149d82f979773942e1191",
    "livebench_legacy15_slot_feasibility_v1.py": "9502f2237af47b422376f2babcd3b7ca3e47eda1",
    "livebench_if_score_bound_v1.py": "f8e4f2bb0d537bfd4646c4037cf74238f7b0d4df",
    "livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
}

PUBLIC = {
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "historical_generator_blob": "6ff390d6885cf90f88d9d36959735cb327613edc",
    "instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "registry_blob": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "score_process_blob": "8ce01747887ec0792c8f024e1972e34ece781676",
}

FORBIDDEN_SAMPLE = ("help", "rock", "western", "sentence", "signal")
END_PHRASE = "Is there anything else I can help with?"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def literal_assignment(text: str, name: str):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"assignment not found: {name}")


def verify_public_source() -> dict:
    paths = {
        "instructions_blob": LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions.py",
        "instructions_util_blob": LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions_util.py",
        "registry_blob": LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions_registry.py",
        "score_process_blob": LIVEBENCH / "livebench/process_results/instruction_following/utils.py",
    }
    for key, path in paths.items():
        actual = git_blob_sha(path.read_bytes())
        assert actual == PUBLIC[key], (key, actual, PUBLIC[key])

    util = paths["instructions_util_blob"].read_text(encoding="utf-8")
    words = literal_assignment(util, "WORD_LIST")
    assert all(w in words for w in FORBIDDEN_SAMPLE)

    ins = paths["instructions_blob"].read_text(encoding="utf-8")
    assert literal_assignment(ins, "_NUM_KEYWORDS") == 5
    endings = literal_assignment(ins, "_ENDING_OPTIONS")
    assert END_PHRASE in endings
    assert 're.search(r"\\b" + word + r"\\b", value, flags=re.IGNORECASE)' in ins
    assert "return value.endswith(self._end_phrase)" in ins

    reg = paths["registry_blob"].read_text(encoding="utf-8")
    assert '_KEYWORD + "forbidden_words": {_KEYWORD + "forbidden_words"}' in reg
    assert '_STARTEND + "end_checker": {_STARTEND + "end_checker"}' in reg

    generator = subprocess.check_output(
        ["git", "-C", str(LIVEBENCH), "cat-file", "-p", PUBLIC["historical_generator_blob"]],
        text=True,
    )
    assert 'keywords:forbidden_words' in generator
    assert 'startend:end_checker' in generator
    assert "np.random.choice(all_constraints, draw, replace=False)" in generator
    assert "build_instruction.build_description()" in generator

    score_text = paths["score_process_blob"].read_text(encoding="utf-8")
    assert "avg_score = (score_1 + score_2) / 2" in score_text

    return {
        "keyword_pool_size": len(words),
        "all_five_forbidden_sample_words_in_word_list": True,
        "forbidden_default_keyword_count": 5,
        "mandatory_end_phrase_in_ending_options": True,
        "instruction_pair_publicly_compatible": True,
        "historical_generator_contains_both_ids": True,
        "frozen_score_formula_present": True,
    }


def verify_candidate() -> dict:
    for name, expected in EXPECTED.items():
        actual = git_blob_sha((SUBJECT / name).read_bytes())
        assert actual == expected, (name, actual, expected)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        runtime = root / "canonical" / "runtime"
        tests = root / "canonical" / "tests"
        runtime.mkdir(parents=True)
        tests.mkdir(parents=True)
        for name in [
            "livebench_generator_support_threshold_route_falsifier_v2.py",
            "livebench_legacy15_slot_feasibility_v1.py",
            "livebench_if_score_bound_v1.py",
            "livebench_legacy15_composition_archetypes_v1.py",
        ]:
            shutil.copy2(SUBJECT / name, runtime / name)
        shutil.copy2(
            SUBJECT / "test_livebench_generator_support_threshold_route_falsifier_v2.py",
            tests / "test_livebench_generator_support_threshold_route_falsifier_v2.py",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q",
             str(tests / "test_livebench_generator_support_threshold_route_falsifier_v2.py")],
            check=True,
            env=env,
        )
        sys.path.insert(0, str(root))
        try:
            from canonical.runtime.livebench_generator_support_threshold_route_falsifier_v2 import verify
            out = verify()
        finally:
            sys.path.pop(0)

    assert out["status"] == "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED"
    assert out["collision_word"] == "help"
    assert out["mandatory_end_phrase"] == END_PHRASE
    assert tuple(out["counterexample_forbidden_words"]) == FORBIDDEN_SAMPLE
    assert out["maximum_counterexample_score"] == "1/4"
    assert out["target_predicate_floor"] == "657/1000"
    return out


def main() -> None:
    source = verify_public_source()
    candidate = verify_candidate()
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_THRESHOLD_ROUTE_1900_FASTLANE_VERIFICATION_V3",
        "status": "PASS__INDEPENDENT_FASTLANE_MINIMAL_END_FORBIDDEN_PROOF",
        "brain_pr": 1900,
        "subject_blob_shas": EXPECTED,
        "public_source_bindings": PUBLIC,
        "public_source_facts": source,
        "candidate_status": candidate["status"],
        "collision_word": candidate["collision_word"],
        "mandatory_end_phrase": candidate["mandatory_end_phrase"],
        "counterexample_forbidden_words": candidate["counterexample_forbidden_words"],
        "maximum_counterexample_score": candidate["maximum_counterexample_score"],
        "target_predicate_floor": candidate["target_predicate_floor"],
        "terminal_rows_read": 0,
        "terminal_row_metadata_read": 0,
        "acceptance_credit": False,
    }
    path = ROOT / "livebench-threshold-route-1900-fastlane-receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
