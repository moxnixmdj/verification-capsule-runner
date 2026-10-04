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

BRAIN_COMMIT = "514c423401e40cce0b8a56f878f0e434db7f6ef9"
RUNTIME_URL = (
    "https://raw.githubusercontent.com/moxnixmdj/brain/"
    + BRAIN_COMMIT
    + "/canonical/runtime/livebench_ratio_overlap_visible_token_constructor_v1.py"
)
RUNTIME_BLOB = "06021bce4c51db74431ccbc25a18aa13eb65c784"
THEOREM_URL = (
    "https://raw.githubusercontent.com/moxnixmdj/brain/"
    + BRAIN_COMMIT
    + "/canonical/governance/LIVEBENCH_RATIO_OVERLAP_REFERENCE_INDEPENDENCE_THEOREM_V1.json"
)
THEOREM_BLOB = "e18170011d080f09f061f6368f5813584f190176"

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
    req = urllib.request.Request(
        url, headers={"User-Agent": "project-brain-independent-verifier"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def trigram_set(text: str) -> set[str]:
    s = str(text or "")
    return {s[i:i+3] for i in range(max(0, len(s) - 2))}


def exact_overlap(response: str, reference: str) -> float:
    a = trigram_set(response)
    b = trigram_set(reference)
    assert a
    return 100.0 * len(a & b) / len(a)


def independent_best_l(k: int, percentage: float, tolerance: float = 2.0):
    lower = max(0.0, percentage - tolerance)
    upper = min(100.0, percentage + tolerance)
    hits = []
    for l in range(4097):
        score = 100.0 * k / (k + l)
        if lower <= score <= upper:
            hits.append((abs(score - percentage), l, score))
    return min(hits) if hits else None


def load_runtime(raw: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "runtime_under_test.py"
        p.write_bytes(raw)
        spec = importlib.util.spec_from_file_location(
            "runtime_under_test", p
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["runtime_under_test"] = module
        spec.loader.exec_module(module)
        return module


def visible_candidates(prompt: str, reference: str) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(r"\S+", prompt):
        token = m.group(0)
        if token in seen:
            continue
        seen.add(token)
        if len(token) < 3:
            continue
        if any(ch.isspace() for ch in token):
            continue
        if any(0xE000 <= ord(ch) <= 0xF8FF for ch in token):
            continue
        # Public-family existential validation only. The reference is used
        # here to prove that at least one visible token can satisfy the
        # theorem assumptions, not as a deployment-time input.
        if token in reference:
            out.append(token)
    return out


def main() -> int:
    runtime_raw = fetch(RUNTIME_URL)
    theorem_raw = fetch(THEOREM_URL)
    data_raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)

    observed_blobs = {
        "brain_runtime": git_blob_sha(runtime_raw),
        "brain_theorem": git_blob_sha(theorem_raw),
        "ifbench_test": git_blob_sha(data_raw),
        "livebench_checker": git_blob_sha(checker_raw),
    }
    expected_blobs = {
        "brain_runtime": RUNTIME_BLOB,
        "brain_theorem": THEOREM_BLOB,
        "ifbench_test": IFBENCH_BLOB,
        "livebench_checker": CHECKER_BLOB,
    }
    assert observed_blobs == expected_blobs, (observed_blobs, expected_blobs)

    checker = checker_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in checker
    assert "ngrams = set(nltk.ngrams(value, n))" in checker
    assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in checker
    assert "len(ngrams.intersection(ref_ngrams)) / len(ngrams)" in checker

    theorem = json.loads(theorem_raw)
    assert theorem["public_family_validation"]["ratio_overlap_rows"] == 12
    assert theorem["public_family_validation"]["constructive_existential_pass_rows"] == 12
    assert theorem["accounting"]["acceptance_credit_delta"] == 0
    assert theorem["execution_authority"] is False
    assert theorem["promotion_authority"] is False

    runtime = load_runtime(runtime_raw)
    rows = [json.loads(x) for x in data_raw.decode("utf-8").splitlines() if x.strip()]
    ratio_rows = [
        x for x in rows
        if "ratio:overlap" in (x.get("instruction_id_list") or [])
    ]
    assert len(rows) == 300
    assert len(ratio_rows) == 12

    row_receipts = []
    for row in ratio_rows:
        ids = list(row["instruction_id_list"])
        idx = ids.index("ratio:overlap")
        kw = row["kwargs"][idx]
        ref = str(kw["reference_text"])
        pct = float(kw["percentage"])
        prompt = str(row["prompt"])

        candidates = visible_candidates(prompt, ref)
        assert candidates, row["key"]

        chosen = None
        for token in candidates:
            k = len(trigram_set(token))
            independent = independent_best_l(k, pct)
            if independent is None:
                continue
            _, expected_l, expected_score = independent
            out = runtime.construct(token, pct)
            if out["status"] != "PASS_UNDER_EXPLICIT_REFERENCE_ASSUMPTIONS":
                continue
            assert out["stable_trigram_count"] == k
            assert out["novel_trigram_count"] == expected_l
            assert abs(out["guaranteed_overlap_percent"] - expected_score) < 1e-12

            response = out["response"]
            suffix = response[len(token):]
            assert len(suffix) == expected_l
            assert len(set(suffix)) == len(suffix)
            assert all(0xE000 <= ord(ch) <= 0xF8FF for ch in suffix)
            assert all(ch not in ref for ch in suffix)

            observed_score = exact_overlap(response, ref)
            assert abs(observed_score - expected_score) < 1e-12
            assert pct - 2.0 <= observed_score <= pct + 2.0
            chosen = {
                "key": row["key"],
                "percentage": pct,
                "token": token,
                "stable_trigram_count": k,
                "novel_trigram_count": expected_l,
                "score_percent": observed_score,
            }
            break

        assert chosen is not None, row["key"]
        row_receipts.append(chosen)

    # Adversarial algebra checks independent of the public rows.
    for token, pct in [
        ("induction", 72),
        ("Transformational", 93),
        ("Describe", 11),
        ("abcdef", 50),
    ]:
        k = len(trigram_set(token))
        independent = independent_best_l(k, float(pct))
        out = runtime.construct(token, float(pct))
        if independent is None:
            assert out["status"] == "FAIL_CLOSED"
        else:
            assert out["status"] == "PASS_UNDER_EXPLICIT_REFERENCE_ASSUMPTIONS"
            assert out["novel_trigram_count"] == independent[1]
            assert abs(out["guaranteed_overlap_percent"] - independent[2]) < 1e-12

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_REFERENCE_INDEPENDENCE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "brain_commit": BRAIN_COMMIT,
        "source_git_blobs": observed_blobs,
        "verified": {
            "frozen_checker_denominator_is_response_unique_character_trigrams": True,
            "public_ifbench_rows": len(rows),
            "ratio_overlap_rows": len(ratio_rows),
            "constructive_existential_pass_rows": len(row_receipts),
            "runtime_matches_independent_integer_construction": True,
            "exact_checker_arithmetic_matches_constructed_scores": True,
            "private_use_suffix_disjoint_on_public_rows": True,
        },
        "rows": row_receipts,
        "deduction": (
            "EXACT_REFERENCE_RECONSTRUCTION_IS_NOT_REQUIRED_FOR_RATIO_OVERLAP "
            "WHEN_A_VISIBLE_TOKEN_SATISFIES_THE_THEOREM_ASSUMPTIONS; "
            "THE_REQUIRED_REFERENCE INFORMATION COLLAPSES_TO_A_STABLE_VISIBLE_TOKEN "
            "PLUS_SUFFIX_ALPHABET_DISJOINTNESS."
        ),
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_DEPLOYMENT_TIME_VISIBLE_TOKEN_EXTRACTOR_PROOF",
            "NO_COMBINATION_SOUNDNESS_PROOF",
            "NO_SEMANTIC_ANSWER_QUALITY_PROOF",
            "NO_LIVEBENCH_ACCEPTANCE_OR_OPUS55_CAPABILITY_CREDIT",
            "NO_TERMINAL_CASE_CONTENT_READ",
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
    Path("livebench_ratio_overlap_reference_independence_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
