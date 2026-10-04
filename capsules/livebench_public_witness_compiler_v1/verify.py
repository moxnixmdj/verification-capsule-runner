#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import re
import string
import sys
import urllib.request

import nltk

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_DIR = ROOT / "subject"
COMPILER = SUBJECT_DIR / "livebench_public_witness_compiler_v1.py"
DETECTOR = SUBJECT_DIR / "livebench_public_description_detector_v1.py"
EXPECTED_COMPILER_BLOB = "f381c46d011c03b25ada9e8780308463fbf6c290"
EXPECTED_DETECTOR_BLOB = "ffe3569f0cf0c6dedc4fc5714ae435fd5c5691d9"
PIN = "8f8e5c381a16e3f24257776edd53471fe86f8091"

LEGACY_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/instruction_following_eval/instructions.py"
MODERN_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/ifbench/instructions.py"
LEGACY_REGISTRY_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/instruction_following_eval/instructions_registry.py"
MODERN_REGISTRY_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{PIN}/livebench/if_runner/ifbench/instructions_registry.py"

LEGACY_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
MODERN_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
MODERN_REGISTRY_BLOB = "adfed4832877566e62970257b50c6fa32c302fb2"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_subject(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def literal_string_expr(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return literal_string_expr(node.left) + literal_string_expr(node.right)
    raise AssertionError(("NON_LITERAL_DESCRIPTION_PATTERN", ast.dump(node)))


def registered_classes(registry_source: str) -> list[str]:
    tree = ast.parse(registry_source)
    value = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in node.targets):
            value = node.value
            break
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "INSTRUCTION_DICT":
            value = node.value
            break
    assert isinstance(value, ast.Dict), ast.dump(value) if value else None
    out = []
    for item in value.values:
        assert isinstance(item, ast.Attribute), ast.dump(item)
        assert isinstance(item.value, ast.Name) and item.value.id == "instructions", ast.dump(item)
        out.append(item.attr)
    return out


def description_patterns(source: str, class_name: str) -> list[str]:
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "build_description")
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "_description_pattern"
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                out.append(literal_string_expr(node.value))
    assert out, class_name
    return out


def module_constant(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(("MISSING_MODULE_CONSTANT", name))


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


def exact_class(source: str, name: str, legacy_comparison_relation=None):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    ns = {
        "Instruction": Instruction,
        "instructions_util": Util,
        "re": re,
        "json": json,
        "string": string,
        "nltk": nltk,
    }
    if legacy_comparison_relation is not None:
        ns["_COMPARISON_RELATION"] = legacy_comparison_relation
    exec(compile(ast.fix_missing_locations(module), f"<pinned:{name}>", "exec"), ns)
    return ns[name]


def main() -> int:
    compiler_bytes = COMPILER.read_bytes()
    detector_bytes = DETECTOR.read_bytes()
    assert git_blob(compiler_bytes) == EXPECTED_COMPILER_BLOB
    assert git_blob(detector_bytes) == EXPECTED_DETECTOR_BLOB

    legacy_raw = fetch(LEGACY_URL)
    modern_raw = fetch(MODERN_URL)
    legacy_registry_raw = fetch(LEGACY_REGISTRY_URL)
    modern_registry_raw = fetch(MODERN_REGISTRY_URL)
    assert git_blob(legacy_raw) == LEGACY_BLOB
    assert git_blob(modern_raw) == MODERN_BLOB
    assert git_blob(legacy_registry_raw) == LEGACY_REGISTRY_BLOB
    assert git_blob(modern_registry_raw) == MODERN_REGISTRY_BLOB

    legacy = legacy_raw.decode("utf-8")
    modern = modern_raw.decode("utf-8")
    legacy_registry = legacy_registry_raw.decode("utf-8")
    modern_registry = modern_registry_raw.decode("utf-8")

    sys.path.insert(0, str(SUBJECT_DIR))
    detector = load_subject("livebench_public_description_detector_v1", DETECTOR)
    compiler = load_subject("livebench_public_witness_compiler_v1", COMPILER)

    legacy_classes = registered_classes(legacy_registry)
    modern_classes = registered_classes(modern_registry)
    assert len(legacy_classes) == 25
    assert len(modern_classes) == 58
    assert len(legacy_classes) + len(modern_classes) == 83
    exact_registered = set(legacy_classes + modern_classes)
    assert exact_registered == set(detector.PUBLIC_DESCRIPTION_PATTERNS)

    pattern_count = 0
    for name in legacy_classes:
        expected = description_patterns(legacy, name)
        got = detector.PUBLIC_DESCRIPTION_PATTERNS[name]
        assert got["family"] == "legacy"
        assert sorted(got["patterns"]) == sorted(expected), (name, got["patterns"], expected)
        pattern_count += len(expected)
    for name in modern_classes:
        expected = description_patterns(modern, name)
        got = detector.PUBLIC_DESCRIPTION_PATTERNS[name]
        assert got["family"] == "modern"
        assert sorted(got["patterns"]) == sorted(expected), (name, got["patterns"], expected)
        pattern_count += len(expected)
    assert pattern_count == 86

    self_cov = detector.verify_registry_self_coverage()
    assert self_cov["status"] == "PASS", self_cov
    assert self_cov["checker_count"] == 83
    assert self_cov["pattern_count"] == 86

    comparison_relation = module_constant(legacy, "_COMPARISON_RELATION")

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
         {"_forbidden_words": ["forbidden", "ban"]}),
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
        out = compiler.compile_witness(prompt)
        assert out["status"] == "PASS", (prompt, out)
        assert out["matched_checkers"] == [expected_route], (expected_route, out)
        assert out["terminal_case_content_used"] is False
        assert out["hidden_metadata_used"] is False
        assert out["network_used"] is False
        assert out["incremental_spend_usd"] == 0
        assert out["model_dependency_count"] == 0
        assert out["terminal_authority"] is False

        cls = exact_class(
            source,
            class_name,
            comparison_relation if source is legacy else None,
        )
        checker = cls()
        for key, value in attrs.items():
            setattr(checker, key, value)
        assert checker.check_following(out["response"]) is True, {
            "prompt": prompt,
            "class": class_name,
            "response": out["response"],
        }
        verified.append(expected_route)

    unsupported = compiler.compile_witness(
        "Task. Use at least 7 unique words in the response."
    )
    assert unsupported["status"] == "BLOCKED", unsupported
    assert unsupported["reason"] == "UNSUPPORTED_PUBLIC_CHECKER_DETECTED", unsupported
    assert "UniqueWordCountChecker" in unsupported["detected_unsupported_checkers"]

    conjunction = compiler.compile_witness(
        "Task. Answer with at least 5 words. Wrap your entire response with double quotation marks."
    )
    assert conjunction["status"] == "BLOCKED", conjunction
    assert conjunction["reason"] == "MULTI_CHECKER_COMBINATION_NOT_PROVED", conjunction

    verdict = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUBLIC_WITNESS_COMPILER_INDEPENDENT_VERIFICATION_V2",
        "status": "PASS",
        "brain_compiler_blob": EXPECTED_COMPILER_BLOB,
        "brain_detector_blob": EXPECTED_DETECTOR_BLOB,
        "pinned_livebench_commit": PIN,
        "pinned_public_source_blobs": {
            "legacy_instructions": LEGACY_BLOB,
            "modern_instructions": MODERN_BLOB,
            "legacy_registry": LEGACY_REGISTRY_BLOB,
            "modern_registry": MODERN_REGISTRY_BLOB,
        },
        "active_registry_checker_count": 83,
        "exact_description_pattern_count": pattern_count,
        "detector_registry_exactly_matches_pinned_active_registries_and_pattern_assignments": True,
        "detector_synthetic_pattern_self_coverage": True,
        "exact_public_checker_body_pass_count": len(verified),
        "exact_public_checker_body_passes": verified,
        "unsupported_public_checker_fail_closed": True,
        "recognized_multi_checker_fail_closed": True,
        "terminal_cases_consumed": 0,
        "terminal_case_content_used": False,
        "hidden_instruction_ids_or_kwargs_used": False,
        "acceptance_credit_delta": 0,
        "promotion_authority": False,
        "remaining_hard_nonclaims": [
            "DOES_NOT_PROVE_JOINT_WITNESS_CONSTRUCTION_FOR_MULTI_CHECKER_PROMPTS",
            "DOES_NOT_PROVE_FOUR_OR_MORE_TERMINAL_CASE_RECOVERIES",
            "DOES_NOT_CLOSE_LIVEBENCH_IF_GE_65_7",
        ],
    }
    print(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
