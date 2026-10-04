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

RATIO_RE = re.compile(r"Maintain a trigram overlap of (\d+)% \(±2%\) with the provided reference text\.")
KEYWORD_RE = re.compile(r'The response must include keyword "?[^"\s]+"? in the \d+-(?:st|nd|rd|th) sentence\.')
CONSONANT_DESC = "Ensure each word in your response has at least one consonant cluster (two or more consonants together)."

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def trigrams(s: str) -> list[str]:
    return [s[i:i+3] for i in range(max(0, len(s)-2))]

def exact_overlap_percent(value: str, reference_text: str) -> tuple[int, int, float]:
    a = set(trigrams(value))
    b = set(trigrams(reference_text))
    assert a
    hits = len(a & b)
    return hits, len(a), 100.0 * hits / len(a)

def derive_from_visible_prompt(prompt: str) -> tuple[int, str]:
    # This public-family constructor sees only rendered prompt text.
    x = norm_ws(prompt).replace("\u200b", "")
    m = RATIO_RE.search(x)
    assert m, "ratio description not visible"
    target = int(m.group(1))
    x = RATIO_RE.sub(" ", x)
    x = KEYWORD_RE.sub(" ", x)
    x = x.replace(CONSONANT_DESC, " ")
    base = norm_ws(x).replace("\u200b", "").strip()
    assert base
    return target, base

def private_use_tail(forbidden: str, count: int) -> str:
    chars = []
    cp = 0xE000
    while len(chars) < count:
        assert cp <= 0xF8FF
        ch = chr(cp)
        cp += 1
        if ch not in forbidden:
            chars.append(ch)
    return "".join(chars)

def construct_from_visible_base(base: str, target: int) -> dict:
    # Search only whitespace-free substrings of the prompt-derived base.
    # For a chosen segment with H unique trigrams, every internal trigram is
    # guaranteed to occur in any reference whose whitespace-normalization is base.
    # Appending T distinct private-use characters absent from base contributes
    # exactly T new unique trigrams, all guaranteed misses.
    best = None
    for token in re.findall(r"\S+", base):
        for start in range(len(token)):
            for end in range(start + 3, len(token) + 1):
                segment = token[start:end]
                seg_tris = trigrams(segment)
                if len(set(seg_tris)) != len(seg_tris):
                    continue
                h = len(seg_tris)
                for t in range(0, 256):
                    total = h + t
                    pct = 100.0 * h / total
                    err = abs(pct - target)
                    if err <= 2.0 + 1e-12:
                        rec = {
                            "segment": segment,
                            "segment_len": len(segment),
                            "hit_trigrams": h,
                            "tail_count": t,
                            "total_trigrams": total,
                            "predicted_percent": pct,
                            "absolute_error": err,
                        }
                        if best is None or (rec["absolute_error"], rec["total_trigrams"]) < (best["absolute_error"], best["total_trigrams"]):
                            best = rec
    assert best is not None, f"no prompt-only constructor found for target={target}"
    tail = private_use_tail(base + best["segment"], best["tail_count"])
    response = best["segment"] + tail
    # Constructor proof check against visible base only.
    h2, m2, p2 = exact_overlap_percent(response, base)
    assert h2 == best["hit_trigrams"]
    assert m2 == best["total_trigrams"]
    assert abs(p2 - target) <= 2.0 + 1e-12
    best["response"] = response
    return best

def main() -> int:
    raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB, (git_blob_sha(raw), IFBENCH_BLOB)
    assert git_blob_sha(checker_raw) == CHECKER_BLOB, (git_blob_sha(checker_raw), CHECKER_BLOB)

    checker = checker_raw.decode("utf-8")
    for required in [
        "class NGramOverlapChecker",
        "n = 3",
        "ngrams = set(nltk.ngrams(value, n))",
        "ref_ngrams = set(nltk.ngrams(self._reference_text, n))",
        "overlap = len(ngrams.intersection(ref_ngrams)) / len(ngrams)",
        "self._percentage - 2 <= overlap * 100 <= self._percentage + 2",
    ]:
        assert required in checker, required

    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows) == 300

    receipts = []
    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        i = ids.index("ratio:overlap")
        kwargs = list(row.get("kwargs") or [])
        kw = kwargs[i]
        exact_ref = str(kw["reference_text"])
        hidden_target = int(kw["percentage"])

        # Construction derives target and normalized base from visible prompt only.
        visible_target, visible_base = derive_from_visible_prompt(str(row.get("prompt") or ""))
        assert visible_target == hidden_target
        assert norm_ws(exact_ref) == visible_base

        witness = construct_from_visible_base(visible_base, visible_target)
        response = witness.pop("response")

        # Hidden exact reference is used only for independent post-hoc verification.
        exact_h, exact_m, exact_pct = exact_overlap_percent(response, exact_ref)
        assert exact_h == witness["hit_trigrams"]
        assert exact_m == witness["total_trigrams"]
        assert abs(exact_pct - visible_target) <= 2.0 + 1e-12

        receipts.append({
            "key": str(row.get("key")),
            "instruction_ids": ids,
            "target_percent": visible_target,
            "segment_len": witness["segment_len"],
            "hit_trigrams": witness["hit_trigrams"],
            "tail_count": witness["tail_count"],
            "total_trigrams": witness["total_trigrams"],
            "exact_verified_percent": exact_pct,
            "absolute_error": abs(exact_pct - visible_target),
        })

    assert len(receipts) == 12
    assert all(abs(r["exact_verified_percent"] - r["target_percent"]) <= 2.0 + 1e-12 for r in receipts)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_NGRAM_WHITESPACE_INVARIANT_CONSTRUCTOR_PUBLIC_VERIFICATION_V1",
        "status": "PASS",
        "source_git_blobs": {
            "ifbench_test": git_blob_sha(raw),
            "livebench_ifbench_instructions": git_blob_sha(checker_raw),
        },
        "public_population": {
            "rows": len(rows),
            "ratio_overlap_rows": len(receipts),
            "prompt_only_base_extraction_pass": len(receipts),
            "prompt_only_ngram_constructor_pass": len(receipts),
            "exact_raw_reference_posthoc_checker_pass": len(receipts),
        },
        "deduction": [
            "ON_ALL_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS_EXACT_RAW_REFERENCE_WHITESPACE_IS_NOT_NECESSARY_TO_CONSTRUCT_A_PASSING_NGRAMOVERLAPCHECKER_WITNESS",
            "WHITESPACE_NORMALIZED_BASE_TEXT_PLUS_VISIBLE_TARGET_PERCENT_IS_SUFFICIENT_ON_THE_PINNED_PUBLIC_POPULATION",
            "CONSTRUCTION_USES_ONLY_A_WHITESPACE_FREE_VISIBLE_BASE_SUBSTRING_AND_DISTINCT_PRIVATE_USE_SENTINEL_CHARACTERS_ABSENT_FROM_THE_VISIBLE_BASE",
            "HIDDEN_EXACT_REFERENCE_TEXT_IS_USED_ONLY_POSTHOC_TO_VERIFY_THE_CONSTRUCTOR_AND_NOT_AS_CONSTRUCTOR_INPUT",
        ],
        "rows": receipts,
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_CLAIM_EVERY_POSSIBLE_RATIO_OVERLAP_PROMPT_HAS_A_SUFFICIENT_VISIBLE_SUBSTRING",
            "NO_CLAIM_THE_RATIO_ONLY_WITNESS_JOINTLY_SATISFIES_EVERY_OTHER_CONSTRAINT_IN_ARBITRARY_COMBINATIONS",
            "NO_LIVEBENCH_ACCEPTANCE_EXECUTION_PROMOTION_OR_FRESH_REALITY_CREDIT",
        ],
    }
    Path("livebench_ngram_whitespace_invariant_constructor_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
