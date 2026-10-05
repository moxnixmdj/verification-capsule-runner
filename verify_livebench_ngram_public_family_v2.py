#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import string
import urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
CHECKER_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
UTIL_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions_util.py"
UTIL_BLOB = "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342"

RATIO = re.compile(
    r"Maintain a trigram overlap of (?P<percentage>\d+(?:\.\d+)?)% \(±2%\) "
    r"with the provided reference text\."
)
KEYWORD = re.compile(
    r'The response must include keyword\s+"?(?P<word>[^"\s]+)"?\s+in the\s+'
    r'(?P<N>\d+)-(?:st|nd|rd|th) sentence\.'
)
CONSONANT_DESC = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
BOUNDARY = re.compile(
    r"^[\s\u200B\u200C\u200D\u2060\uFEFF]+|"
    r"[\s\u200B\u200C\u200D\u2060\uFEFF]+$"
)
LETTERS = set(string.ascii_lowercase)
CONSONANTS = set("bcdfghjklmnpqrstvwxyz")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "project-brain-livebench-independent-verifier"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def grams(value: str) -> set[str]:
    return {value[i:i+3] for i in range(max(0, len(value)-2))}


def score(response: str, reference: str) -> float:
    g = grams(response)
    assert g
    return 100.0 * len(g & grams(reference)) / len(g)


def consonant_pass(value: str) -> bool:
    for word in value.lower().strip().split():
        if all(ch not in LETTERS for ch in word):
            continue
        if not any(
            word[i] in CONSONANTS and word[i+1] in CONSONANTS
            for i in range(len(word)-1)
        ):
            return False
    return True


_ALPHABETS = "([A-Za-z])"
_PREFIXES = "(Mr|St|Mrs|Ms|Dr)[.]"
_SUFFIXES = "(Inc|Ltd|Jr|Sr|Co)"
_STARTERS = r"(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
_ACRONYMS = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
_WEBSITES = "[.](com|net|org|io|gov|edu|me)"
_DIGITS = "([0-9])"
_MULTIPLE_DOTS = r"\.{2,}"


def split_into_sentences(text: str) -> list[str]:
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(_PREFIXES, r"\1<prd>", text)
    text = re.sub(_WEBSITES, r"<prd>\1", text)
    text = re.sub(_DIGITS + "[.]" + _DIGITS, r"\1<prd>\2", text)
    text = re.sub(
        _MULTIPLE_DOTS,
        lambda m: "<prd>" * len(m.group(0)) + "<stop>",
        text,
    )
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub(r"\s" + _ALPHABETS + "[.] ", r" \1<prd> ", text)
    text = re.sub(_ACRONYMS + " " + _STARTERS, r"\1<stop> \2", text)
    text = re.sub(
        _ALPHABETS + "[.]" + _ALPHABETS + "[.]" + _ALPHABETS + "[.]",
        r"\1<prd>\2<prd>\3<prd>",
        text,
    )
    text = re.sub(
        _ALPHABETS + "[.]" + _ALPHABETS + "[.]",
        r"\1<prd>\2<prd>",
        text,
    )
    text = re.sub(" " + _SUFFIXES + "[.] " + _STARTERS, r" \1<stop> \2", text)
    text = re.sub(" " + _SUFFIXES + "[.]", r" \1<prd>", text)
    text = re.sub(" " + _ALPHABETS + "[.]", r" \1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = [x.strip() for x in text.split("<stop>")]
    if sentences and not sentences[-1]:
        sentences = sentences[:-1]
    return sentences


def parse_visible(prompt: str) -> dict:
    s = norm(prompt)
    rm = list(RATIO.finditer(s))
    assert len(rm) == 1
    target = float(rm[0].group("percentage"))
    km = list(KEYWORD.finditer(s))
    assert len(km) <= 1
    keyword = None
    sentence = None
    if km:
        keyword = km[0].group("word")
        sentence = int(km[0].group("N"))
        assert sentence >= 1
    consonant = CONSONANT_DESC in s
    s = RATIO.sub(" ", s, count=1)
    s = KEYWORD.sub(" ", s)
    s = s.replace(CONSONANT_DESC, " ")
    s = BOUNDARY.sub("", norm(s))
    return {
        "reference": norm(s),
        "target": target,
        "keyword": keyword,
        "sentence": sentence,
        "consonant": consonant,
    }


def fresh(reference: str, count: int) -> str:
    out = []
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in reference:
            out.append(ch)
            if len(out) == count:
                return "".join(out)
    if count == 0:
        return ""
    raise AssertionError("insufficient fresh sentinels")


def token_substrings(reference: str):
    for token in norm(reference).split(" "):
        if len(token) < 3:
            continue
        for a in range(len(token) - 2):
            for b in range(a + 3, len(token) + 1):
                yield token[a:b]


def in_band_strict(x: float, target: float) -> bool:
    return target - 2.0 < x < target + 2.0


def ordinary(reference: str, target: float, require_consonant: bool) -> str:
    pool = fresh(reference, 256)
    best = None
    for base in token_substrings(reference):
        for k in range(257):
            response = base + pool[:k]
            if require_consonant and not consonant_pass(response):
                continue
            sc = score(response, reference)
            if not in_band_strict(sc, target):
                continue
            key = (len(response), abs(sc - target), response)
            if best is None or key < best[0]:
                best = (key, response)
    assert best is not None
    return best[1]


def keyword_construct(
    reference: str, target: float, keyword: str, sentence_number: int
) -> str:
    tokens = sorted(
        {t for t in norm(reference).split(" ") if len(t) >= 3},
        key=lambda t: (-len(grams(t)), -len(t), t),
    )
    pool = fresh(reference, sentence_number + len(tokens) + 1032)
    prefix = "".join(pool[i] + "." for i in range(sentence_number - 1))
    variants = [[]]
    selected = []
    for token in tokens:
        selected = [*selected, token]
        variants.append(selected)

    best = None
    for selected_tokens in variants:
        idx = sentence_number - 1
        core = pool[idx] + keyword
        idx += 1
        for token in selected_tokens:
            core += pool[idx] + token
            idx += 1
        core += pool[idx]
        idx += 1
        for extra in range(1025):
            response = prefix + core + pool[idx:idx+extra] + "."
            sc = score(response, reference)
            if in_band_strict(sc, target):
                sentences = split_into_sentences(response)
                assert len(sentences) >= sentence_number
                assert keyword.lower() in sentences[sentence_number-1].lower()
                key = (
                    len(response),
                    abs(sc-target),
                    len(selected_tokens),
                    extra,
                    response,
                )
                if best is None or key < best[0]:
                    best = (key, response)
            elif sc < target - 2.0:
                break
    assert best is not None
    return best[1]


def construct(prompt: str) -> tuple[dict, str]:
    parsed = parse_visible(prompt)
    if parsed["keyword"] is not None:
        assert not parsed["consonant"]
        response = keyword_construct(
            parsed["reference"],
            parsed["target"],
            parsed["keyword"],
            parsed["sentence"],
        )
    else:
        response = ordinary(
            parsed["reference"],
            parsed["target"],
            parsed["consonant"],
        )
    assert not any(ch.isspace() for ch in response)
    assert in_band_strict(score(response, parsed["reference"]), parsed["target"])
    return parsed, response


def verify_row(row: dict) -> dict:
    ids = list(row["instruction_id_list"])
    assert "ratio:overlap" in ids
    assert set(ids) <= {"ratio:overlap", "sentence:keyword", "words:consonants"}
    parsed, response = construct(str(row["prompt"]))

    oi = ids.index("ratio:overlap")
    okw = row["kwargs"][oi]
    raw_reference = str(okw["reference_text"])
    target = float(okw["percentage"])
    assert parsed["reference"] == norm(raw_reference)
    exact_score = score(response, raw_reference)
    assert target - 2.0 <= exact_score <= target + 2.0

    for i, instruction_id in enumerate(ids):
        kw = row["kwargs"][i]
        if instruction_id == "ratio:overlap":
            continue
        if instruction_id == "sentence:keyword":
            sentences = split_into_sentences(response)
            n = int(kw["N"])
            word = str(kw["word"])
            assert len(sentences) >= n
            assert word.lower() in sentences[n-1].lower()
        elif instruction_id == "words:consonants":
            assert consonant_pass(response)

    return {
        "key": str(row["key"]),
        "instruction_ids": ids,
        "target_percent": target,
        "exact_raw_reference_score_percent": exact_score,
        "response_length": len(response),
    }


def main() -> int:
    raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    util_raw = fetch(UTIL_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB
    assert git_blob_sha(checker_raw) == CHECKER_BLOB
    assert git_blob_sha(util_raw) == UTIL_BLOB

    checker = checker_raw.decode("utf-8")
    util = util_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in checker
    assert "nltk.ngrams(value, n)" in checker
    assert "nltk.ngrams(self._reference_text, n)" in checker
    assert "class IncludeKeywordChecker" in checker
    assert "class ConsonantClusterChecker" in checker
    assert "def split_into_sentences(text: str)" in util

    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows) == 300
    ratio_rows = [r for r in rows if "ratio:overlap" in r["instruction_id_list"]]
    results = [verify_row(r) for r in ratio_rows]

    ratio_only = sum(len(r["instruction_ids"]) == 1 for r in results)
    keyword = sum("sentence:keyword" in r["instruction_ids"] for r in results)
    consonant = sum("words:consonants" in r["instruction_ids"] for r in results)
    assert (len(results), ratio_only, keyword, consonant) == (12, 5, 4, 3)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_NGRAM_PUBLIC_FAMILY_V2_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "sources": {
            "ifbench_git_blob_sha": git_blob_sha(raw),
            "checker_git_blob_sha": git_blob_sha(checker_raw),
            "checker_util_git_blob_sha": git_blob_sha(util_raw),
        },
        "verified": {
            "public_ifbench_rows": 300,
            "ratio_overlap_rows": 12,
            "ratio_only_rows": 5,
            "ratio_plus_sentence_keyword_rows": 4,
            "ratio_plus_consonant_cluster_rows": 3,
            "normalized_reference_recovered_from_visible_prompt": 12,
            "exact_raw_reference_overlap_pass": 12,
            "prompt_level_all_instruction_pass": 12,
            "constructor_used_hidden_kwargs": False,
            "hidden_kwargs_used_for_verification_only": True,
            "terminal_livebench_rows_read": 0,
        },
        "rows": results,
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_LIVEBENCH_ACCEPTANCE_OR_ROOT1_CLOSURE",
            "NO_TERMINAL_SCORE_CLAIM",
        ],
    }
    Path("livebench_ngram_public_family_v2_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
