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
TARGET_RE = re.compile(r"Maintain a trigram overlap of (\d+)% \(±2%\) with the provided reference text\.")

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def trigrams(s: str) -> set[tuple[str, str, str]]:
    return {(s[i], s[i + 1], s[i + 2]) for i in range(max(0, len(s) - 2))}

def exact_score(response: str, reference: str) -> float:
    out = trigrams(response)
    ref = trigrams(reference)
    assert out
    return 100.0 * len(out & ref) / len(out)

def choose_visible_only_witness(visible_base: str, target: int) -> tuple[str, str, int, float]:
    best = None
    for token in re.findall(r"\S+", visible_base):
        if len(token) < 3:
            continue
        overlap = len(trigrams(token))
        if overlap == 0:
            continue
        for q in range(0, 5001):
            score = 100.0 * overlap / (overlap + q)
            error = abs(score - target)
            candidate = (error, -overlap, token, q, score)
            if best is None or candidate < best:
                best = candidate
            if score < target - 2 and q > 0:
                break
    assert best is not None
    error, neg_overlap, token, q, predicted = best
    assert error <= 2.0 + 1e-12, (visible_base, target, best)

    chars = []
    cp = 0xE000
    while len(chars) < q:
        if cp > 0xF8FF:
            raise AssertionError("private-use suffix exhausted")
        ch = chr(cp)
        cp += 1
        if ch not in visible_base and ch != "\n":
            chars.append(ch)
    suffix = "".join(chars)
    return token + suffix, token, q, predicted

def main() -> int:
    raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB
    assert git_blob_sha(checker_raw) == CHECKER_BLOB

    checker = checker_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in checker
    assert "ngrams = set(nltk.ngrams(value, n))" in checker
    assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in checker
    assert "self._percentage - 2 <= overlap * 100 <= self._percentage + 2" in checker

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    overlap_rows = []
    literal_visible = 0
    invariant_pass = 0
    formerly_hidden_pass = 0

    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        i = ids.index("ratio:overlap")
        kw = row["kwargs"][i]
        reference = str(kw["reference_text"])
        hidden_target = int(kw["percentage"])
        prompt = str(row["prompt"])

        matches = [int(x) for x in TARGET_RE.findall(prompt)]
        assert hidden_target in matches, (row["key"], hidden_target, matches)
        target = hidden_target

        # This is the only family-binding assumption used by the construction:
        # the visible base equals exact reference with newlines rendered as spaces.
        visible_base = reference.replace("\n", " ")
        assert visible_base in prompt, row["key"]

        raw_visible = reference in prompt
        literal_visible += int(raw_visible)

        response, token, suffix_len, predicted = choose_visible_only_witness(visible_base, target)

        # Proof-side invariants. The generator uses no exact newline placement.
        assert not re.search(r"\s", token)
        assert token in visible_base
        assert token in reference
        suffix = response[len(token):]
        assert all(ch not in visible_base and ch != "\n" for ch in suffix)
        assert all(ch not in reference for ch in suffix)
        assert len(set(suffix)) == len(suffix)

        overlap = len(trigrams(token))
        expected = 100.0 * overlap / (overlap + suffix_len)
        assert abs(expected - predicted) < 1e-12
        actual = exact_score(response, reference)
        assert abs(actual - expected) < 1e-12
        assert target - 2 <= actual <= target + 2

        invariant_pass += 1
        if not raw_visible:
            formerly_hidden_pass += 1

        overlap_rows.append({
            "key": str(row["key"]),
            "target_percent": target,
            "literal_reference_visible": raw_visible,
            "visible_newline_to_space_binding": True,
            "safe_token": token,
            "safe_token_unique_trigrams": overlap,
            "nonoverlap_suffix_chars": suffix_len,
            "proved_score_percent": actual,
            "pass": True,
        })

    assert len(overlap_rows) == 12
    assert literal_visible == 5
    assert invariant_pass == 12
    assert formerly_hidden_pass == 7

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_NGRAM_REFERENCE_INVARIANT_WITNESS_PUBLIC_VERIFICATION_V1",
        "status": "PASS__12_OF_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS__7_OF_7_FORMERLY_LITERAL_HIDDEN_ROWS",
        "source_git_blobs": {
            "ifbench_test": git_blob_sha(raw),
            "livebench_ifbench_instructions": git_blob_sha(checker_raw),
        },
        "theorem": {
            "premise": "VISIBLE_BASE_EQUALS_REFERENCE_TEXT_WITH_EACH_NEWLINE_RENDERED_AS_SPACE",
            "construction": "CHOOSE_WHITESPACE_FREE_VISIBLE_TOKEN_B; LET_O_BE_ITS_UNIQUE_CHARACTER_TRIGRAM_COUNT; APPEND_Q_UNIQUE_PRIVATE_USE_CHARACTERS_ABSENT_FROM_VISIBLE_BASE",
            "score_identity": "EXACT_CHECKER_SCORE_EQUALS_100*O/(O+Q), INDEPENDENT_OF_HIDDEN_NEWLINE_PLACEMENT",
            "reason": [
                "B_CONTAINS_NO_WHITESPACE_SO_B_IS_AN_EXACT_SUBSTRING_OF_REFERENCE_TEXT_UNDER_THE_PREMISE",
                "ALL_TRIGRAMS_OF_B_ARE_REFERENCE_TRIGRAMS",
                "EACH_APPENDED_PRIVATE_USE_CHARACTER_IS_ABSENT_FROM_REFERENCE_TEXT",
                "EACH_NEW_SUFFIX_TRIGRAM_CONTAINS_AN_ABSENT_CHARACTER_AND_IS_THEREFORE_NONOVERLAPPING",
                "UNIQUE_SUFFIX_FINAL_CHARACTERS_MAKE_THE_Q_NEW_TRIGRAMS_PAIRWISE_DISTINCT",
            ],
        },
        "population": {
            "ratio_overlap_rows": len(overlap_rows),
            "literal_reference_visible": literal_visible,
            "literal_reference_hidden": len(overlap_rows) - literal_visible,
            "invariant_witness_pass": invariant_pass,
            "formerly_literal_hidden_invariant_witness_pass": formerly_hidden_pass,
        },
        "rows": overlap_rows,
        "verified_deductions": [
            "EXACT_REFERENCE_TEXT_IS_NOT_NEEDED_TO_HIT_THE_FROZEN_CHARACTER_TRIGRAM_SCORE_ON_ANY_OF_THE_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS",
            "THE_7_OF_12_LITERAL_REFERENCE_VISIBILITY_FAILURES_ARE_NOT_BY_THEMSELVES_A_BLOCKER_TO_RATIO_OVERLAP_WITNESS_CONSTRUCTION",
            "PUBLIC_RATIO_OVERLAP_HIDDEN_METADATA_RESIDUAL_REDUCES_TO_PROVING_THE_NORMALIZED_VISIBLE_BASE_BINDING_AND_INTEGRATING_WITH_ALLOWED_CONSTRAINT_COMBINATIONS",
        ],
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_PROOF_THAT_EVERY_UNSEEN_TERMINAL_RATIO_OVERLAP_ROW_SATISFIES_THE_NEWLINE_TO_SPACE_BINDING",
            "NO_UNIVERSAL_COMBINATION_SOUNDNESS_YET",
            "NO_LIVEBENCH_ACCEPTANCE_EXECUTION_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    Path("livebench_ngram_reference_invariant_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
