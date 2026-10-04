#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import urllib.request
from pathlib import Path

import nltk
from ifbench import instructions

EXPECTED_SUBJECT_BLOB = "b7fc14cb8ba707cf20d07c2d0d1d5cc891558164"
IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
LIVEBENCH_CHECKER_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
LIVEBENCH_CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_subject():
    path = Path("subject/livebench_ratio_reference_free_constructor_v1.py")
    raw = path.read_bytes()
    actual = git_blob_sha(raw)
    assert actual == EXPECTED_SUBJECT_BLOB, (actual, EXPECTED_SUBJECT_BLOB)
    spec = importlib.util.spec_from_file_location("ratio_subject", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, actual


def exact_ratio(candidate: str, reference_text: str, percentage: int) -> float:
    checker = instructions.NGramOverlapChecker("ratio:overlap")
    checker.build_description(reference_text=reference_text, percentage=percentage)
    assert checker.check_following(candidate)
    a = set(nltk.ngrams(candidate, 3))
    b = set(nltk.ngrams(reference_text, 3))
    return 100.0 * len(a.intersection(b)) / len(a)


def exact_companions(candidate: str, ids: list[str], kwargs: list[dict]) -> dict[str, bool]:
    result = {}
    for index, instruction_id in enumerate(ids):
        kw = kwargs[index] if index < len(kwargs) else {}
        if instruction_id == "sentence:keyword":
            checker = instructions.IncludeKeywordChecker(instruction_id)
            checker.build_description(**kw)
            result[instruction_id] = bool(checker.check_following(candidate))
        elif instruction_id == "words:consonants":
            checker = instructions.ConsonantClusterChecker(instruction_id)
            checker.build_description()
            result[instruction_id] = bool(checker.check_following(candidate))
    return result


def main() -> int:
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)

    subject, subject_blob = load_subject()
    data_raw = fetch(IFBENCH_URL)
    checker_raw = fetch(LIVEBENCH_CHECKER_URL)
    assert git_blob_sha(data_raw) == IFBENCH_BLOB
    assert git_blob_sha(checker_raw) == LIVEBENCH_CHECKER_BLOB

    checker_source = checker_raw.decode("utf-8")
    required_source_atoms = [
        "class NGramOverlapChecker",
        "ngrams = set(nltk.ngrams(value, n))",
        "ref_ngrams = set(nltk.ngrams(self._reference_text, n))",
        "class IncludeKeywordChecker",
        "class ConsonantClusterChecker",
    ]
    for atom in required_source_atoms:
        assert atom in checker_source, atom

    rows = [json.loads(line) for line in data_raw.decode("utf-8").splitlines() if line.strip()]
    receipts = []
    ratio_rows = 0
    normalization_relation_pass = 0
    predicted_equals_exact = 0
    ratio_pass = 0
    keyword_rows = 0
    keyword_pass = 0
    consonant_rows = 0
    consonant_pass = 0

    for row_index, row in enumerate(rows):
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue

        ratio_rows += 1
        prompt = str(row.get("prompt") or "")

        # Critical contamination firewall: candidate generation occurs before
        # this verifier reads hidden kwargs or reference_text.
        constructed = subject.construct_ratio_overlap_candidate(prompt)
        candidate = constructed["candidate"]

        kwargs = list(row.get("kwargs") or [])
        ratio_index = ids.index("ratio:overlap")
        ratio_kw = kwargs[ratio_index]
        reference = str(ratio_kw["reference_text"])
        percentage = int(ratio_kw["percentage"])

        visible_relation = subject._norm_ws(reference) == constructed["visible_base"]
        normalization_relation_pass += int(visible_relation)
        assert visible_relation, row_index

        exact = exact_ratio(candidate, reference, percentage)
        predicted = float(constructed["predicted_overlap_percent"])
        predicted_exact = abs(predicted - exact) < 1e-12
        predicted_equals_exact += int(predicted_exact)
        assert predicted_exact, (row_index, predicted, exact)

        in_band = abs(exact - percentage) <= 2.0
        ratio_pass += int(in_band)
        assert in_band, (row_index, percentage, exact)

        companions = exact_companions(candidate, ids, kwargs)
        if "sentence:keyword" in ids:
            keyword_rows += 1
            keyword_pass += int(companions.get("sentence:keyword") is True)
            assert companions.get("sentence:keyword") is True, row_index
        if "words:consonants" in ids:
            consonant_rows += 1
            consonant_pass += int(companions.get("words:consonants") is True)
            assert companions.get("words:consonants") is True, row_index

        receipts.append({
            "row_index": row_index,
            "target_percent": percentage,
            "predicted_percent": predicted,
            "exact_percent": exact,
            "ids": ids,
            "visible_normalized_reference_relation": visible_relation,
            "ratio_pass": in_band,
            "companion_pass": companions,
            "candidate_length": len(candidate),
        })

    expected = {
        "ratio_rows": 12,
        "normalization_relation_pass": 12,
        "predicted_equals_exact": 12,
        "ratio_pass": 12,
        "keyword_rows": 4,
        "keyword_pass": 4,
        "consonant_rows": 3,
        "consonant_pass": 3,
    }
    actual = {
        "ratio_rows": ratio_rows,
        "normalization_relation_pass": normalization_relation_pass,
        "predicted_equals_exact": predicted_equals_exact,
        "ratio_pass": ratio_pass,
        "keyword_rows": keyword_rows,
        "keyword_pass": keyword_pass,
        "consonant_rows": consonant_rows,
        "consonant_pass": consonant_pass,
    }
    assert actual == expected, (actual, expected)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_RATIO_REFERENCE_FREE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "subject_git_blob_sha": subject_blob,
        "source_git_blobs": {
            "ifbench_test": git_blob_sha(data_raw),
            "livebench_ifbench_instructions": git_blob_sha(checker_raw),
        },
        "actual": actual,
        "rows": receipts,
        "verified_theorem": (
            "FOR_PINNED_PUBLIC_RATIO_OVERLAP_ROWS_WHERE_VISIBLE_BASE_EQUALS_"
            "NORMALIZED_REFERENCE__EXACT_REFERENCE_BYTES_ARE_UNNECESSARY__"
            "VISIBLE_NONWHITESPACE_TRIGRAMS_PLUS_FRESH_SENTINEL_TRIGRAMS_"
            "CONSTRUCT_AN_EXACTLY_PREDICTABLE_IN_BAND_SCORE"
        ),
        "hard_nonclaims": [
            "NO_TERMINAL_LIVEBENCH_200_CASE_POPULATION_EQUIVALENCE",
            "NO_ACCEPTANCE_OR_FAMILY_CREDIT",
            "NO_EXECUTION_OR_PROMOTION_AUTHORITY",
            "NO_GENERALIZATION_BEYOND_THE_EXPLICIT_NORMALIZED_REFERENCE_RELATION",
            "NO_TERMINAL_CASE_CONTENT_USED_TO_BUILD_THE_CONSTRUCTOR",
        ],
    }
    Path("livebench_ratio_reference_free_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
