#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import re
import string
import urllib.request

import nltk

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_public_witness_compiler_v1.py"
EXPECTED_SUBJECT_BLOB = "25acb3193166af8d394ac3fdb4bd89400a1f76d7"
PIN = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/instruction_following_eval/instructions.py"
MODERN_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/ifbench/instructions.py"
LEGACY_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
MODERN_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


class Util:
    nltk = nltk

    @staticmethod
    def count_words(text: str) -> int:
        tokenizer = nltk.tokenize.RegexpTokenizer(r"\w+")
        return len(tokenizer.tokenize(text))

    @staticmethod
    def count_sentences(text: str) -> int:
        tokenizer = nltk.data.load("nltk:tokenizers/punkt/english.pickle")
        return len(tokenizer.tokenize(text))


class Instruction:
    pass


def exact_class(source: str, name: str):
    tree = ast.parse(source)
    node = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    ns = {
        "Instruction": Instruction,
        "instructions_util": Util,
        "re": re,
        "json": json,
        "string": string,
        "nltk": nltk,
    }
    exec(compile(ast.fix_missing_locations(module), f"<pinned:{name}>", "exec"), ns)
    return ns[name]


def load_candidate():
    data = SUBJECT.read_bytes()
    assert git_blob(data) == EXPECTED_SUBJECT_BLOB, (git_blob(data), EXPECTED_SUBJECT_BLOB)
    spec = importlib.util.spec_from_file_location("candidate", SUBJECT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    legacy_raw = fetch(LEGACY_URL)
    modern_raw = fetch(MODERN_URL)
    assert git_blob(legacy_raw) == LEGACY_BLOB
    assert git_blob(modern_raw) == MODERN_BLOB
    legacy = legacy_raw.decode("utf-8")
    modern = modern_raw.decode("utf-8")
    candidate = load_candidate()

    cases = [
        ("Task. Answer with at least 7 words.", "legacy:NumberOfWords", legacy, "NumberOfWords",
         {"_num_words": 7, "_comparison_relation": "at least"}),
        ("Task. Your response should contain at least 3 sentences.", "legacy:NumberOfSentences", legacy, "NumberOfSentences",
         {"_num_sentences_threshold": 3, "_comparison_relation": "at least"}),
        ("Task. There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***", "legacy:ParagraphChecker", legacy, "ParagraphChecker",
         {"_num_paragraphs": 3}),
        ("Task. Entire output should be wrapped in JSON format.", "legacy:JsonFormat", legacy, "JsonFormat", {}),
        ("Task. Answer with one of the following options: ['Alpha', 'Beta']", "legacy:ConstrainedResponseChecker", legacy, "ConstrainedResponseChecker",
         {"_constrained_responses": ["Alpha", "Beta"]}),
        ("Task. Wrap your entire response with double quotation marks.", "legacy:QuotationChecker", legacy, "QuotationChecker", {}),
        ("Task. The response must contain between 8 and 11 words.", "modern:WordCountRangeChecker", modern, "WordCountRangeChecker",
         {"_min_words": 8, "_max_words": 11}),
        ("Task. Include exactly 4 numbers in the response; do not use commas within the numbers.", "modern:NumbersCountChecker", modern, "NumbersCountChecker",
         {"_count_numbers": 4}),
        ("Task. The output should not contain any whitespace.", "modern:NoWhitespaceChecker", modern, "NoWhitespaceChecker", {}),
        ("Task. Write the entire response in title case (capitalize the first letter of every word).", "modern:TitleCaseChecker", modern, "TitleCaseChecker", {}),
        ("Task. Use this exact template for your response: My Answer: [answer] My Conclusion: [conclusion] Future Outlook: [outlook]", "modern:OutputTemplateChecker", modern, "OutputTemplateChecker", {}),
        ("Task. Answer with a newline-separated list of items, instead of bullet points use SEPARATOR.", "modern:SpecialBulletPointsChecker", modern, "SpecialBulletPointsChecker",
         {"_bullet_marker": "SEPARATOR"}),
        ("Task. Finish your response with this exact phrase THE END. No other words should follow this phrase.", "legacy:EndChecker", legacy, "EndChecker",
         {"_end_phrase": "THE END"}),
        ("Task. In your entire response, refrain from the use of any commas.", "legacy:CommaChecker", legacy, "CommaChecker", {}),
        ("Task. Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.", "legacy:TitleChecker", legacy, "TitleChecker", {}),
        ("Task. Include keywords ['alpha', 'beta'] in the response.", "legacy:KeywordChecker", legacy, "KeywordChecker",
         {"_keywords": ["alpha", "beta"]}),
        ("Task. Do not include keywords ['forbidden', 'ban'] in the response.", "legacy:ForbiddenWords", legacy, "ForbiddenWords",
         {"_forbidden_words": ["ban", "forbidden"]}),
        ("Task. In your response, the word alpha should appear at least 3 times.", "legacy:KeywordFrequencyChecker", legacy, "KeywordFrequencyChecker",
         {"_keyword": "alpha", "_frequency": 3, "_comparison_relation": "at least"}),
        ("Task. Your answer must contain exactly 4 bullet points.", "legacy:BulletListChecker", legacy, "BulletListChecker",
         {"_num_bullets": 4}),
        ("Task. Highlight at least 3 sections in your answer with markdown, i.e. *highlighted section*.", "legacy:HighlightSectionChecker", legacy, "HighlightSectionChecker",
         {"_num_highlights": 3}),
        ("Task. At the end of your response, please explicitly add a postscript starting with P.S.", "legacy:PostscriptChecker", legacy, "PostscriptChecker",
         {"_postscript_marker": "P.S."}),
    ]

    verified = []
    for prompt, expected_route, source, class_name, attrs in cases:
        out = candidate.compile_witness(prompt)
        assert out["status"] == "PASS", (prompt, out)
        assert out["matched_checkers"] == [expected_route], (expected_route, out)
        assert out["terminal_case_content_used"] is False
        assert out["hidden_metadata_used"] is False
        assert out["network_used"] is False
        assert out["incremental_spend_usd"] == 0
        assert out["model_dependency_count"] == 0
        assert out["terminal_authority"] is False
        cls = exact_class(source, class_name)
        checker = cls()
        for key, value in attrs.items():
            setattr(checker, key, value)
        assert checker.check_following(out["response"]) is True, {
            "prompt": prompt,
            "class": class_name,
            "response": out["response"],
        }
        verified.append(expected_route)

    unknown = candidate.compile_witness("Task. Use an unsupported public instruction form.")
    assert unknown["status"] == "BLOCKED"
    assert unknown["reason"] == "NO_SUPPORTED_PUBLIC_DESCRIPTION"

    conjunction = candidate.compile_witness(
        "Task. Answer with at least 5 words. Wrap your entire response with double quotation marks."
    )
    assert conjunction["status"] == "BLOCKED"
    assert conjunction["reason"] == "MULTI_CHECKER_COMBINATION_NOT_PROVED"

    verdict = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUBLIC_WITNESS_COMPILER_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "brain_candidate_blob": EXPECTED_SUBJECT_BLOB,
        "pinned_livebench_commit": PIN,
        "pinned_public_source_blobs": {
            "legacy_instructions": LEGACY_BLOB,
            "modern_instructions": MODERN_BLOB,
        },
        "exact_public_checker_body_pass_count": len(verified),
        "exact_public_checker_body_passes": verified,
        "unsupported_prompt_fail_closed": True,
        "recognized_multi_checker_fail_closed": True,
        "terminal_cases_consumed": 0,
        "terminal_case_content_used": False,
        "hidden_instruction_ids_or_kwargs_used": False,
        "acceptance_credit_delta": 0,
        "promotion_authority": False,
        "hard_nonclaims": [
            "DOES_NOT_PROVE_COMPLETE_DETECTION_OF_ALL_83_PUBLIC_CHECKER_DESCRIPTIONS",
            "DOES_NOT_PROVE_MULTI_CHECKER_CONJUNCTION_SOUNDNESS",
            "DOES_NOT_PROVE_FOUR_OR_MORE_TERMINAL_CASE_RECOVERIES",
            "DOES_NOT_CLOSE_LIVEBENCH_IF_GE_65_7",
        ],
    }
    print(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
