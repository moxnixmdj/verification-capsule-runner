#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

BRAIN_COMMIT = "70851966a938a5913159662cf82729b2ffede11d"
SOLVER_URL = (
    "https://raw.githubusercontent.com/moxnixmdj/brain/"
    + BRAIN_COMMIT
    + "/canonical/runtime/ifbench_ratio_overlap_prompt_only_solver_v1.py"
)
SOLVER_BLOB = "88c80cb3e259cd136418d79d1c7bef45aaa4d95f"
IFBENCH_URL = (
    "https://raw.githubusercontent.com/allenai/IFBench/"
    "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
)
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
CHECKER_URL = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/"
    "8f8e5c381a16e3f24257776edd53471fe86f8091/"
    "livebench/if_runner/ifbench/instructions.py"
)
CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def grams(s: str) -> set[str]:
    s = str(s or "")
    return {s[i:i+3] for i in range(max(0, len(s)-2))}


def overlap(value: str, reference: str) -> float:
    g = grams(value)
    assert g
    return 100.0 * len(g & grams(reference)) / len(g)


def consonant_checker(value: str) -> bool:
    letters = set("abcdefghijklmnopqrstuvwxyz")
    consonants = set("bcdfghjklmnpqrstvwxyz")
    for word in value.lower().strip().split():
        if all(char not in letters for char in word):
            continue
        if not any(word[i] in consonants and word[i+1] in consonants for i in range(len(word)-1)):
            return False
    return True


def simple_sentence_split(value: str) -> list[str]:
    return [x.strip() for x in re.split(r"[.!?]", value) if x.strip()]


def load_solver(raw: bytes):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "solver_under_test.py"
        path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location("solver_under_test", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod


def main() -> int:
    solver_raw = fetch(SOLVER_URL)
    data_raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)

    assert git_blob_sha(solver_raw) == SOLVER_BLOB
    assert git_blob_sha(data_raw) == IFBENCH_BLOB
    assert git_blob_sha(checker_raw) == CHECKER_BLOB

    checker = checker_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in checker
    assert "ngrams = set(nltk.ngrams(value, n))" in checker
    assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in checker
    assert "self._percentage - 2 <= overlap * 100 <= self._percentage + 2" in checker

    solver = load_solver(solver_raw)
    rows = [json.loads(x) for x in data_raw.decode("utf-8").splitlines() if x.strip()]
    results = []

    for row_index, row in enumerate(rows):
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        ratio_i = ids.index("ratio:overlap")
        kwargs = list(row.get("kwargs") or [])
        ratio_kw = kwargs[ratio_i]
        exact_ref = str(ratio_kw.get("reference_text") or "")
        target = int(ratio_kw.get("percentage"))

        # The subject receives prompt text only. Hidden public kwargs are used
        # solely below as an independent oracle after candidate construction.
        out = solver.solve_supported_public_prompt(str(row.get("prompt") or ""))
        assert out["status"] == "PASS__WHITESPACE_INVARIANT_TRIGRAM_CONSTRUCTION", (row_index, out)
        candidate = str(out["response"])
        assert candidate and not any(ch.isspace() for ch in candidate)

        projection = out["projection"]
        assert norm_ws(exact_ref) == projection["reference_proxy"], row_index

        proxy_score = float(out["computed_overlap_percent"])
        exact_score = overlap(candidate, exact_ref)
        assert abs(proxy_score - exact_score) < 1e-12, (row_index, proxy_score, exact_score)
        assert target - 2 <= exact_score <= target + 2, (row_index, target, exact_score)

        if "sentence:keyword" in ids:
            j = ids.index("sentence:keyword")
            kw = kwargs[j]
            word = str(kw.get("word") or kw.get("keyword") or "")
            n = int(kw.get("N"))
            sentences = simple_sentence_split(candidate)
            assert len(sentences) >= n
            assert word.lower() in sentences[n-1].lower()

        if "words:consonants" in ids:
            assert consonant_checker(candidate)

        results.append(
            {
                "row_index": row_index,
                "target": target,
                "proxy_score": proxy_score,
                "exact_score": exact_score,
                "instruction_ids": ids,
                "candidate_len": len(candidate),
            }
        )

    assert len(results) == 12, len(results)
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_WHITESPACE_INVARIANT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "brain_commit": BRAIN_COMMIT,
        "solver_git_blob_sha": git_blob_sha(solver_raw),
        "ifbench_git_blob_sha": git_blob_sha(data_raw),
        "checker_git_blob_sha": git_blob_sha(checker_raw),
        "ratio_overlap_rows": len(results),
        "rows_with_exact_proxy_score_equality": sum(abs(x["proxy_score"] - x["exact_score"]) < 1e-12 for x in results),
        "rows_within_frozen_checker_tolerance": sum(x["target"] - 2 <= x["exact_score"] <= x["target"] + 2 for x in results),
        "results": results,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "NO_TERMINAL_LIVEBENCH_ACCEPTANCE_CREDIT",
            "NO_UNSEEN_TERMINAL_CASES",
            "NO_UNIVERSAL_83_FAMILY_COMPOSITION_PROOF",
        ],
    }
    Path("livebench_ratio_overlap_whitespace_invariant_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
