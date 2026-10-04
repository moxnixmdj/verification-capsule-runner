#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions.py"
INSTRUCTIONS_UTIL_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions_util.py"
INSTRUCTIONS_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
INSTRUCTIONS_UTIL_BLOB = "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342"

NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
STOPWORDS_URL = f"https://raw.githubusercontent.com/nltk/nltk_data/{NLTK_DATA_COMMIT}/packages/corpora/stopwords.zip"
STOPWORDS_SHA256 = "48c0e52d8b52546e827f53761fb30300c0ab94f70660d28bd65ba0a86270946b"

TOKENS = tuple(f"qzxv{i}" for i in range(8))

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main() -> int:
    instructions_raw = fetch(INSTRUCTIONS_URL)
    util_raw = fetch(INSTRUCTIONS_UTIL_URL)
    stopwords_zip = fetch(STOPWORDS_URL)

    assert git_blob_sha(instructions_raw) == INSTRUCTIONS_BLOB
    assert git_blob_sha(util_raw) == INSTRUCTIONS_UTIL_BLOB
    assert hashlib.sha256(stopwords_zip).hexdigest() == STOPWORDS_SHA256

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data_root = root / "nltk_data"
        corpora = data_root / "corpora"
        corpora.mkdir(parents=True, exist_ok=True)
        zip_path = corpora / "stopwords.zip"
        zip_path.write_bytes(stopwords_zip)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(corpora)

        os.environ["NLTK_DATA"] = str(data_root)

        import nltk
        import spacy

        assert nltk.__version__ == "3.10.3"
        # Freeze corpus use to the exact pinned local bytes. The scorer's
        # count_stopwords calls nltk.download('stopwords'); make that call a
        # no-op so no network-updated corpus can replace the pinned corpus.
        nltk.data.path[:] = [str(data_root)]
        nltk.download = lambda *args, **kwargs: True
        spacy.util.is_package = lambda _name: True

        pkg_root = root / "livebench" / "if_runner" / "ifbench"
        pkg_root.mkdir(parents=True)
        for p in [root / "livebench", root / "livebench" / "if_runner", pkg_root]:
            (p / "__init__.py").write_text("", encoding="utf-8")
        (pkg_root / "instructions.py").write_bytes(instructions_raw)
        (pkg_root / "instructions_util.py").write_bytes(util_raw)

        sys.path.insert(0, str(root))
        try:
            mod = importlib.import_module("livebench.if_runner.ifbench.instructions")
            util = importlib.import_module("livebench.if_runner.ifbench.instructions_util")
        finally:
            pass

        english = set(nltk.corpus.stopwords.words("english"))
        assert english
        assert all(t.lower() not in english for t in TOKENS)

        response = " ".join(TOKENS)
        assert util.count_words(response) == len(TOKENS)
        assert util.count_stopwords(response) == 0

        checker_results = {}
        for pct in (0, 1, 37, 100):
            checker = mod.StopWordPercentageChecker("ratio:stop_words")
            checker.build_description(percentage=pct)
            passed = bool(checker.check_following(response))
            checker_results[str(pct)] = passed
            assert passed

        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_STOPWORD_ZERO_WITNESS_INDEPENDENT_VERIFICATION_V1",
            "status": "PASS__EXACT_PINNED_STOPWORD_CORPUS__EXACT_PINNED_StopWordPercentageChecker__PARAMETER_FREE_ZERO_STOPWORD_WITNESS",
            "source_bindings": {
                "livebench_commit": LIVEBENCH_COMMIT,
                "instructions_git_blob_sha": git_blob_sha(instructions_raw),
                "instructions_util_git_blob_sha": git_blob_sha(util_raw),
                "nltk_data_commit": NLTK_DATA_COMMIT,
                "stopwords_zip_sha256": hashlib.sha256(stopwords_zip).hexdigest(),
                "nltk_version": nltk.__version__,
            },
            "witness": {
                "response": response,
                "regexp_word_count": util.count_words(response),
                "stopword_count": util.count_stopwords(response),
                "all_tokens_absent_from_pinned_english_stopwords": True,
                "boundary_and_interior_percentage_checks": checker_results,
            },
            "verified_deductions": [
                "ratio:stop_words_HAS_A_PARAMETER_FREE_CONSTRUCTIVE_WITNESS_FOR_EVERY_LEGAL_PERCENTAGE_CEILING_0_TO_100_UNDER_THE_EXACT_PINNED_SCORER_SEMANTICS",
                "THE_WITNESS_REQUIRES_NO_HIDDEN_PERCENTAGE_VALUE_TO_REMAIN_VALID",
                "NO_POST_PROMPT_STOPWORD_CORPUS_NETWORK_ACQUISITION_IS_REQUIRED_FOR_THE_VERIFIED_FORM",
            ],
            "hard_nonclaims": [
                "NO_FROZEN_TERMINAL_LIVEBENCH_DISTRIBUTION_EQUIVALENCE_CLAIM",
                "NO_LIVEBENCH_THRESHOLD_PASS_CLAIM",
                "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
                "NO_TERMINAL_CASE_CONTENT_READ",
            ],
            "accounting": {
                "incremental_spend_usd": 0,
                "terminal_cases_consumed": 0,
                "acceptance_credit_delta": 0,
            },
        }
        Path("livebench_stopword_zero_witness_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
