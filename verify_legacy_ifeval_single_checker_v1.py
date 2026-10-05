#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject/legacy_ifeval_single_v1"
RUNTIME = SUB / "canonical/runtime"
SOLVER = RUNTIME / "livebench_legacy_ifeval_single_checker_witness_v1.py"
INVERTER = RUNTIME / "livebench_legacy_ifeval_prompt_inverter_v1.py"
TESTS = SUB / "canonical/tests/test_livebench_legacy_ifeval_single_checker_witness_v1.py"

EXPECTED_BRAIN_BLOBS = {
    "solver": "341b3413493caf8c1cd2e1ab1f18c93d62f4ba87",
    "inverter": "74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a",
    "tests": "dd268944c26a5b0845a8f4ccb09f42061d59af27",
}
UPSTREAM_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
UPSTREAM = {
    "instructions.py": (
        "livebench/if_runner/instruction_following_eval/instructions.py",
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    ),
    "instructions_util.py": (
        "livebench/if_runner/instruction_following_eval/instructions_util.py",
        "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    ),
}


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


assert git_blob(SOLVER.read_bytes()) == EXPECTED_BRAIN_BLOBS["solver"]
assert git_blob(INVERTER.read_bytes()) == EXPECTED_BRAIN_BLOBS["inverter"]
assert git_blob(TESTS.read_bytes()) == EXPECTED_BRAIN_BLOBS["tests"]

# Candidate unit tests first.
sys.path.insert(0, str(SUB))
spec = importlib.util.spec_from_file_location("candidate_tests", TESTS)
testmod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(testmod)
test_obj = testmod.LegacySingleCheckerWitnessTests()
unit_names = sorted(n for n in dir(test_obj) if n.startswith("test_"))
for name in unit_names:
    test_obj.setUp()
    try:
        getattr(test_obj, name)()
    finally:
        test_obj.tearDown()

# Materialize the exact pinned public checker source into an isolated package.
UP = ROOT / "_pinned_legacy_ifeval"
PKG = UP / "instruction_following_eval"
PKG.mkdir(parents=True, exist_ok=True)
(PKG / "__init__.py").write_text("", encoding="utf-8")
upstream_blobs = {}
for local_name, (remote_path, expected_blob) in UPSTREAM.items():
    url = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/{remote_path}"
    data = urllib.request.urlopen(url, timeout=30).read()
    got = git_blob(data)
    assert got == expected_blob, (local_name, got, expected_blob)
    (PKG / local_name).write_bytes(data)
    upstream_blobs[local_name] = got

sys.path.insert(0, str(UP))
instructions = importlib.import_module("instruction_following_eval.instructions")
solver = importlib.import_module("canonical.runtime.livebench_legacy_ifeval_single_checker_witness_v1")

CASES = [
    ("keywords:existence", "KeywordChecker", {"keywords": ["alpha", "beta"]}, None),
    ("keywords:frequency", "KeywordFrequencyChecker", {"keyword": "alpha", "frequency": 2, "relation": "at least"}, None),
    ("keywords:forbidden_words", "ForbiddenWords", {"forbidden_words": ["banana", "orange"]}, None),
    ("keywords:letter_frequency", "LetterFrequencyChecker", {"letter": "z", "let_frequency": 3, "let_relation": "at least"}, None),
    ("language:response_language", "ResponseLanguageChecker", {"language": "en"}, None),
    ("length_constraints:number_sentences", "NumberOfSentences", {"num_sentences": 3, "relation": "at least"}, None),
    ("length_constraints:number_paragraphs", "ParagraphChecker", {"num_paragraphs": 3}, None),
    ("length_constraints:number_words", "NumberOfWords", {"num_words": 5, "relation": "at least"}, None),
    ("length_constraints:nth_paragraph_first_word", "ParagraphFirstWordCheck", {"num_paragraphs": 3, "nth_paragraph": 2, "first_word": "cedar"}, None),
    ("detectable_content:number_placeholders", "PlaceholderChecker", {"num_placeholders": 2}, None),
    ("detectable_content:postscript", "PostscriptChecker", {"postscript_marker": "P.S."}, None),
    ("detectable_format:number_bullet_lists", "BulletListChecker", {"num_bullets": 2}, None),
    ("detectable_format:constrained_response", "ConstrainedResponseChecker", {}, None),
    ("detectable_format:number_highlighted_sections", "HighlightSectionChecker", {"num_highlights": 2}, None),
    ("detectable_format:multiple_sections", "SectionChecker", {"section_spliter": "Section", "num_sections": 2}, None),
    ("detectable_format:json_format", "JsonFormat", {}, None),
    ("detectable_format:title", "TitleChecker", {}, None),
    ("combination:two_responses", "TwoResponsesChecker", {}, None),
    ("combination:repeat_prompt", "RepeatPromptThenAnswer", {"prompt_to_repeat": "Write a safe answer."}, "Write a safe answer. "),
    ("startend:end_checker", "EndChecker", {"end_phrase": "Any other questions?"}, None),
    ("change_case:capital_word_frequency", "CapitalWordFrequencyChecker", {"capital_frequency": 2, "capital_relation": "at least"}, None),
    ("change_case:english_capital", "CapitalLettersEnglishChecker", {}, None),
    ("change_case:english_lowercase", "LowercaseLettersEnglishChecker", {}, None),
    ("punctuation:no_comma", "CommaChecker", {}, None),
    ("startend:quotation", "QuotationChecker", {}, None),
]

results = []
for instruction_id, class_name, kwargs, prefix in CASES:
    checker = getattr(instructions, class_name)(instruction_id)
    description = checker.build_description(**kwargs)
    prompt = (prefix or "") + description
    out = solver.solve(prompt)
    recognized = out.get("instruction_id")
    response = out.get("response")
    followed = bool(response is not None and checker.check_following(response))
    results.append({
        "instruction_id": instruction_id,
        "class_name": class_name,
        "recognized": recognized,
        "status": out.get("status"),
        "exact_check_following": followed,
    })

failed = [r for r in results if r["recognized"] != r["instruction_id"] or not r["exact_check_following"]]
assert len(CASES) == 25
assert not failed, failed

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_IFEVAL_SINGLE_CHECKER_WITNESS_V1_INDEPENDENT_VERIFICATION",
    "status": "PASS",
    "brain_pr": 1782,
    "brain_head": "5132155414d495c5b1b329c6c08275264b46fed8",
    "exact_brain_blobs": EXPECTED_BRAIN_BLOBS,
    "upstream_commit": UPSTREAM_COMMIT,
    "exact_upstream_blobs": upstream_blobs,
    "candidate_unit_tests_executed": unit_names,
    "active_checker_types_verified": 25,
    "all_25_original_check_following_true": True,
    "per_checker": results,
    "terminal_cases_consumed": 0,
    "terminal_prompt_or_kwargs_used": False,
    "acceptance_credit_delta": 0,
    "incremental_spend_usd": 0,
}
(ROOT / "legacy_ifeval_single_checker_v1_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
