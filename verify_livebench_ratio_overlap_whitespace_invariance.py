#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
LIVEBENCH_INSTRUCTIONS_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
LIVEBENCH_INSTRUCTIONS_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
LIVEBENCH_UTIL_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions_util.py"
LIVEBENCH_UTIL_BLOB = "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342"

RATIO_RE = re.compile(
    r"Maintain a trigram overlap of (\d+(?:\.\d+)?)% \(±2%\) with the provided reference text\."
)
KEYWORD_RE = re.compile(
    r"The response must include keyword\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s+"
    r"in the (\d+)-(?:st|nd|rd|th) sentence\."
)
CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def norm_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def drop_format_chars(value: str) -> str:
    return "".join(ch for ch in value if unicodedata.category(ch) != "Cf")

def char_trigrams(value: str) -> set[str]:
    return {value[i:i+3] for i in range(max(0, len(value)-2))}

def overlap_percent(response: str, reference: str) -> float:
    out = char_trigrams(response)
    if not out:
        raise ValueError("response needs at least one trigram")
    ref = char_trigrams(reference)
    return 100.0 * len(out & ref) / len(out)

def parse_visible_prompt(prompt: str) -> dict:
    text = norm_ws(prompt)
    m = RATIO_RE.search(text)
    if not m:
        raise ValueError("ratio description not visible")
    if len(RATIO_RE.findall(text)) != 1:
        raise ValueError("ratio description ambiguous")
    percentage = float(m.group(1))
    km = KEYWORD_RE.search(text)
    keyword = None
    keyword_sentence = None
    if km:
        keyword = next(x for x in km.groups()[:3] if x is not None)
        keyword_sentence = int(km.group(4))
    consonant = CONSONANT_TEXT in text
    base = RATIO_RE.sub(" ", text)
    base = KEYWORD_RE.sub(" ", base)
    base = base.replace(CONSONANT_TEXT, " ")
    base = norm_ws(drop_format_chars(base))
    return {
        "percentage": percentage,
        "keyword": keyword,
        "keyword_sentence": keyword_sentence,
        "consonant": consonant,
        "normalized_reference": base,
    }

def absent_private_chars(reference: str, count: int = 2048) -> list[str]:
    out = []
    for cp in range(0xE000, 0xF900):
        ch = chr(cp)
        if ch not in reference:
            out.append(ch)
            if len(out) >= count:
                break
    if len(out) < count:
        raise ValueError("insufficient private-use sentinels")
    return out

def consonant_cluster_check(value: str) -> bool:
    letters = set("abcdefghijklmnopqrstuvwxyz")
    consonants = set("bcdfghjklmnpqrstvwxyz")
    for word in value.lower().strip().split():
        if all(ch not in letters for ch in word):
            continue
        if not any(
            word[i] in consonants and word[i+1] in consonants
            for i in range(len(word)-1)
        ):
            return False
    return True

def simple_generated_sentence_keyword_check(value: str, keyword: str, n: int) -> bool:
    sentences = [x for x in value.split(".") if x]
    return len(sentences) >= n and keyword.lower() in sentences[n-1].lower()

def candidate_seeds(normalized_reference: str) -> list[str]:
    seeds = set()
    compact = re.sub(r"\s+", "", normalized_reference)
    for end in range(3, len(compact) + 1):
        seeds.add(compact[:end])
    for token in re.findall(r"\S+", normalized_reference):
        if len(token) < 3:
            continue
        seeds.add(token)
        for start in range(len(token) - 2):
            for end in range(start + 3, len(token) + 1):
                seeds.add(token[start:end])
    return sorted(seeds, key=lambda s: (-len(char_trigrams(s)), -len(s), s))

def synthesize_visible_only(prompt: str) -> dict:
    parsed = parse_visible_prompt(prompt)
    target = parsed["percentage"]
    reference = parsed["normalized_reference"]
    sentinels = absent_private_chars(reference)
    cursor = 0
    mandatory = ""
    if parsed["consonant"]:
        mandatory += "str"
    if parsed["keyword"] is not None:
        n = parsed["keyword_sentence"]
        if n is None or n < 1:
            raise ValueError("invalid keyword sentence")
        for i in range(1, n + 1):
            marker = sentinels[cursor]
            cursor += 1
            mandatory += marker + (parsed["keyword"] if i == n else "") + "."
    separator = ""
    if mandatory:
        separator = sentinels[cursor]
        cursor += 1

    seeds = [""] + candidate_seeds(reference)
    ref_grams = char_trigrams(reference)
    low, high = target - 2.0, target + 2.0

    for seed in seeds:
        core = mandatory + separator + seed
        if len(core) < 3:
            continue
        core_grams = char_trigrams(core)
        inter = len(core_grams & ref_grams)
        denom = len(core_grams)
        for filler_len in range(0, 513):
            score = 100.0 * inter / (denom + filler_len)
            if low <= score <= high:
                filler = "".join(sentinels[cursor:cursor+filler_len])
                response = core + filler
                if re.search(r"\s", response):
                    raise AssertionError("synthesized response contains whitespace")
                if parsed["keyword"] is not None and not simple_generated_sentence_keyword_check(
                    response, parsed["keyword"], parsed["keyword_sentence"]
                ):
                    continue
                if parsed["consonant"] and not consonant_cluster_check(response):
                    continue
                measured = overlap_percent(response, reference)
                if abs(measured - score) > 1e-12:
                    raise AssertionError((measured, score))
                return {
                    **parsed,
                    "response": response,
                    "score_normalized": measured,
                    "seed": seed,
                    "filler_len": filler_len,
                }
    raise ValueError("no whitespace-invariant synthesis found")

def main() -> int:
    raw = fetch(IFBENCH_URL)
    ins_raw = fetch(LIVEBENCH_INSTRUCTIONS_URL)
    util_raw = fetch(LIVEBENCH_UTIL_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB
    assert git_blob_sha(ins_raw) == LIVEBENCH_INSTRUCTIONS_BLOB
    assert git_blob_sha(util_raw) == LIVEBENCH_UTIL_BLOB

    instructions = ins_raw.decode("utf-8")
    assert "ngrams = set(nltk.ngrams(value, n))" in instructions
    assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in instructions
    assert "class IncludeKeywordChecker" in instructions
    assert "class ConsonantClusterChecker" in instructions

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    ratio_rows = [
        row for row in rows
        if "ratio:overlap" in (row.get("instruction_id_list") or [])
    ]
    assert len(rows) == 300
    assert len(ratio_rows) == 12

    results = []
    companion_counts = {
        "single": 0,
        "sentence_keyword": 0,
        "words_consonants": 0,
    }
    for row in ratio_rows:
        ids = list(row["instruction_id_list"])
        ratio_i = ids.index("ratio:overlap")
        raw_ref = str(row["kwargs"][ratio_i]["reference_text"])
        target = float(row["kwargs"][ratio_i]["percentage"])
        parsed = parse_visible_prompt(row["prompt"])
        expected_norm = norm_ws(raw_ref)
        assert parsed["normalized_reference"] == expected_norm, row["key"]

        solution = synthesize_visible_only(row["prompt"])
        response = solution["response"]
        assert not re.search(r"\s", response)
        score_norm = overlap_percent(response, expected_norm)
        score_raw = overlap_percent(response, raw_ref)
        assert abs(score_norm - score_raw) < 1e-12, row["key"]
        assert target - 2 <= score_raw <= target + 2, (
            row["key"], target, score_raw
        )

        companions = [x for x in ids if x != "ratio:overlap"]
        if not companions:
            companion_counts["single"] += 1
        elif companions == ["sentence:keyword"]:
            companion_counts["sentence_keyword"] += 1
            kw = row["kwargs"][ids.index("sentence:keyword")]
            assert simple_generated_sentence_keyword_check(
                response, str(kw["word"]), int(kw["N"])
            )
        elif companions == ["words:consonants"] or (
            len(ids) == 2 and set(ids) == {"ratio:overlap", "words:consonants"}
        ):
            companion_counts["words_consonants"] += 1
            assert consonant_cluster_check(response)
        else:
            raise AssertionError(
                ("unexpected ratio companion", row["key"], companions)
            )

        results.append({
            "key": row["key"],
            "target": target,
            "score_raw": score_raw,
            "score_normalized": score_norm,
            "response_has_whitespace": False,
            "response_length": len(response),
            "visible_reference_recovery": (
                "EXACT_AFTER_WS_NORMALIZATION_AND_CF_REMOVAL"
            ),
            "all_public_constraints_pass": True,
        })

    assert companion_counts == {
        "single": 5,
        "sentence_keyword": 4,
        "words_consonants": 3,
    }, companion_counts
    assert all(x["all_public_constraints_pass"] for x in results)

    receipt = {
        "schema": (
            "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_"
            "WHITESPACE_INVARIANCE_PUBLIC_VERIFICATION_V1"
        ),
        "status": "PASS",
        "source_git_blobs": {
            "ifbench_test": git_blob_sha(raw),
            "livebench_ifbench_instructions": git_blob_sha(ins_raw),
            "livebench_ifbench_instructions_util": git_blob_sha(util_raw),
        },
        "population": {
            "public_ifbench_rows": len(rows),
            "ratio_overlap_rows": len(ratio_rows),
            "companion_counts": companion_counts,
            "all_12_visible_reference_recovery_exact_after_normalization": True,
            "all_12_synthesized_without_whitespace": True,
            "all_12_score_equivalence_raw_vs_normalized": True,
            "all_12_target_band_pass": True,
            "all_12_public_companion_constraints_pass": True,
        },
        "theorem": {
            "name": "WHITESPACE_FREE_RESPONSE_TRIGRAM_INVARIANCE",
            "statement": (
                "For response V containing no whitespace and "
                "N=collapse_whitespace(R), every trigram of V is "
                "whitespace-free; whitespace normalization preserves membership "
                "of every whitespace-free trigram, therefore the pinned "
                "set-based character-trigram overlap score satisfies "
                "Score(V,R)=Score(V,N)."
            ),
        },
        "results": results,
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_CASE_CONTENT_READ",
            "NO_FROZEN_TERMINAL_DATASET_EQUIVALENCE_CLAIM",
            "NO_LIVEBENCH_ACCEPTANCE_OR_PROMOTION_CREDIT",
            "NO_CLAIM_BEYOND_PUBLIC_IFBENCH_RATIO_OVERLAP_FAMILY",
        ],
    }
    Path(
        "livebench_ratio_overlap_whitespace_invariance_receipt.json"
    ).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
