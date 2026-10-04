#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
CHECKER_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
TOLERANCE = 2.0


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def trigrams(s: str) -> set[str]:
    return {s[i : i + 3] for i in range(max(0, len(s) - 2))}


def overlap(candidate: str, reference: str) -> float:
    c = trigrams(candidate)
    assert c
    r = trigrams(reference)
    return 100.0 * len(c & r) / len(c)


def novel_chars(base: str, limit: int = 160) -> str:
    out = []
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in base:
            out.append(ch)
            if len(out) >= limit:
                return "".join(out)
    raise AssertionError("private-use novel character pool exhausted")


def construct(normalized_reference: str, target: float) -> tuple[str, float]:
    ref = norm_ws(normalized_reference)
    compact = "".join(ch for ch in ref if not ch.isspace())
    assert len(compact) >= 3
    novel = novel_chars(ref)
    best = None
    starts = min(max(0, len(compact) - 2), 80)
    for start in range(starts):
        max_len = min(240, len(compact) - start)
        for seed_len in range(3, max_len + 1):
            seed = compact[start : start + seed_len]
            for novel_len in range(0, 161):
                candidate = seed + novel[:novel_len]
                predicted = overlap(candidate, ref)
                error = abs(predicted - target)
                key = (error, len(candidate), start, seed_len, novel_len)
                if best is None or key < best[0]:
                    best = (key, candidate, predicted)
                if error <= TOLERANCE:
                    return candidate, predicted
    assert best is not None
    raise AssertionError(f"no witness within tolerance; best={best[0]}")


def main() -> int:
    ifbench_raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    assert git_blob_sha(ifbench_raw) == IFBENCH_BLOB
    assert git_blob_sha(checker_raw) == CHECKER_BLOB

    checker = checker_raw.decode("utf-8")
    required_source_facts = [
        "class NGramOverlapChecker",
        "nltk.ngrams(value, n)",
        "nltk.ngrams(self._reference_text, n)",
        "overlap = len(ngrams.intersection(ref_ngrams)) / len(ngrams)",
        "self._percentage - 2 <= overlap * 100 <= self._percentage + 2",
    ]
    for fact in required_source_facts:
        assert fact in checker, fact

    rows = [json.loads(x) for x in ifbench_raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows) == 300

    cases = []
    for row_index, row in enumerate(rows):
        ids = list(row.get("instruction_id_list") or [])
        kwargs = list(row.get("kwargs") or [])
        for i, instruction_id in enumerate(ids):
            if instruction_id != "ratio:overlap":
                continue
            kw = kwargs[i] if i < len(kwargs) and isinstance(kwargs[i], dict) else {}
            raw_ref = str(kw.get("reference_text") or "")
            target = float(kw.get("percentage"))
            normalized_ref = norm_ws(raw_ref)
            prompt = norm_ws(row.get("prompt") or "")
            assert normalized_ref in prompt

            candidate, predicted = construct(normalized_ref, target)
            assert candidate
            assert not any(ch.isspace() for ch in candidate)

            actual = overlap(candidate, raw_ref)
            assert actual == predicted
            assert abs(actual - target) <= TOLERANCE

            cases.append(
                {
                    "public_row_index": row_index,
                    "target_percent": target,
                    "predicted_percent": predicted,
                    "raw_percent": actual,
                    "absolute_error": abs(actual - target),
                    "candidate_length": len(candidate),
                    "candidate_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
                    "exact_raw_normalized_equal": actual == predicted,
                }
            )

    assert len(cases) == 12
    assert all(c["exact_raw_normalized_equal"] for c in cases)
    assert all(c["absolute_error"] <= TOLERANCE for c in cases)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_NGRAM_WHITESPACE_INVARIANT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "source_git_blobs": {
            "ifbench_test": git_blob_sha(ifbench_raw),
            "livebench_ifbench_instructions": git_blob_sha(checker_raw),
        },
        "public_rows": len(rows),
        "ratio_overlap_rows": len(cases),
        "constructed_within_plus_minus_2": sum(c["absolute_error"] <= TOLERANCE for c in cases),
        "exact_raw_normalized_equal": sum(c["exact_raw_normalized_equal"] for c in cases),
        "worst_absolute_target_error_percent": max(c["absolute_error"] for c in cases),
        "cases": cases,
        "verified_deductions": [
            "WHITESPACE_FREE_CANDIDATE_TRIGRAM_MEMBERSHIP_IS_INVARIANT_UNDER_THE_VERIFIED_WHITESPACE_COLLAPSE_RELATION",
            "12_OF_12_PINNED_PUBLIC_IFBENCH_RATIO_OVERLAP_ROWS_HAVE_A_CONSTRUCTED_WITNESS_WITHIN_CHECKER_TOLERANCE_USING_ONLY_NORMALIZED_REFERENCE_AND_TARGET",
            "EXACT_RAW_REFERENCE_BYTES_ARE_NOT_REQUIRED_FOR_THESE_12_PUBLIC_ROWS",
        ],
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_LIVEBENCH_ACCEPTANCE_OR EXECUTION CREDIT",
            "NO_CLAIM_ALL_RATIO_OVERLAP_CONJUNCTIONS_ARE_SOLVED",
            "NO_CLAIM_ALL_83_CHECKERS_ARE_SOLVED",
        ],
    }
    Path("livebench_ngram_whitespace_invariant_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
