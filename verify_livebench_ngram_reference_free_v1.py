#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import importlib
import inspect
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_ngram_reference_free_v1"
RUNTIME = SUB / "canonical" / "runtime"

SUBJECT_BLOBS = {
    RUNTIME / "livebench_ngram_reference_free_v1.py": "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea",
    RUNTIME / "test_livebench_ngram_reference_free_v1.py": "7259a045e67bc3626c87ed6ce5b8cc1fb1592daa",
}
PUBLIC_IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
PINNED_LIVEBENCH_SCORER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch_public_git_blob(owner: str, repo: str, sha: str) -> bytes:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "brain-independent-verifier"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    data = base64.b64decode(payload["content"])
    assert git_blob_sha(data) == sha
    return data


for path, expected in SUBJECT_BLOBS.items():
    got = git_blob_sha(path.read_bytes())
    assert got == expected, (str(path), got, expected)

sys.path.insert(0, str(SUB))
tests = importlib.import_module("canonical.runtime.test_livebench_ngram_reference_free_v1")
test_names = sorted(n for n in dir(tests) if n.startswith("test_"))
assert len(test_names) == 6, test_names
for name in test_names:
    getattr(tests, name)()

mod = importlib.import_module("canonical.runtime.livebench_ngram_reference_free_v1")
construct_source = inspect.getsource(mod.construct)
assert "reference_text" not in construct_source
assert mod.CONTRACT == "SUFFICIENT_RELATIONAL_CONTRACT_V1"

scorer_source = fetch_public_git_blob(
    "LiveBench", "LiveBench", PINNED_LIVEBENCH_SCORER_BLOB
).decode("utf-8")
start = scorer_source.index("class NGramOverlapChecker")
end = scorer_source.index("\nclass ", start + 10)
ngram_class = scorer_source[start:end]
assert "ngrams = set(nltk.ngrams(value, n))" in ngram_class
assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in ngram_class
assert "word_tokenize" not in ngram_class

public_data = fetch_public_git_blob(
    "allenai", "IFBench", PUBLIC_IFBENCH_BLOB
).decode("utf-8")
rows = [json.loads(line) for line in public_data.splitlines() if line.strip()]
assert len(rows) == 300

audit = mod.audit_public_rows(rows)
assert audit["ratio_rows"] == 12, audit
assert audit["contract_passed"] == 12, audit
assert audit["passed"] == 12, audit
assert audit["all_contract"] is True, audit
assert audit["all_pass"] is True, audit

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_NGRAM_REFERENCE_FREE_PUBLIC_VERIFICATION_V1",
    "status": "PASS",
    "subject_git_blobs": {p.name: h for p, h in SUBJECT_BLOBS.items()},
    "pinned_public_sources": {
        "ifbench_test_git_blob_sha": PUBLIC_IFBENCH_BLOB,
        "livebench_ifbench_instructions_git_blob_sha": PINNED_LIVEBENCH_SCORER_BLOB,
    },
    "verified_scorer_semantics": {
        "character_trigram_set_overlap": True,
        "word_tokenization_used": False,
    },
    "verified_constructor": {
        "reference_text_parameter_absent": True,
        "contract": mod.CONTRACT,
        "synthetic_tests": test_names,
        "synthetic_test_count": len(test_names),
    },
    "public_family_audit": {
        "rows_total": len(rows),
        "ratio_overlap_rows": audit["ratio_rows"],
        "sufficient_contract_passed": audit["contract_passed"],
        "reference_free_constructions_passed_exact_public_reference_scorer": audit["passed"],
        "all_contract": audit["all_contract"],
        "all_pass": audit["all_pass"],
        "per_row": audit["rows"],
    },
    "deduction": [
        "EXACT_RAW_REFERENCE_TEXT_RECOVERY_IS_NOT_NECESSARY_FOR_THE_PINNED_PUBLIC_RATIO_OVERLAP_FAMILY",
        "THE_TWO_ONE_WAY_RELATIONAL_CONDITIONS_C1_C2_ARE_SUFFICIENT_FOR_EXACT_SCORE_CONSTRUCTION",
        "ALL_12_OF_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS_SATISFY_C1_C2_AND_PASS_REFERENCE_FREE_CONSTRUCTION",
    ],
    "hard_nonclaims": [
        "NO_FROZEN_UNSEEN_LIVEBENCH_ROW_BINDING",
        "NO_LIVEBENCH_IF_GE_65_7_ACCEPTANCE_CREDIT",
        "NO_CLAIM_THAT_OTHER_CONSTRAINTS_ON_MULTI_CONSTRAINT_ROWS_ARE_SIMULTANEOUSLY_SATISFIED",
        "NO_TERMINAL_CASE_DATA_USED",
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

out = ROOT / "livebench_ngram_reference_free_public_verification_receipt.json"
out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
