#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"

OVERLAP = re.compile(
    r"Maintain\s+a\s+trigram\s+overlap\s+of\s+"
    r"(?P<percentage>\d+(?:\.\d+)?)%\s*\(±2%\)\s+"
    r"with\s+the\s+provided\s+reference\s+text\.",
    flags=re.I,
)
SENTENCE_KEYWORD = re.compile(
    r"The\s+response\s+must\s+include\s+keyword\s+"
    r"[^\s.]+\s+in\s+the\s+\d+-(?:st|nd|rd|th)\s+sentence\.",
    flags=re.I,
)
CONSONANT_CLUSTER = re.compile(
    r"Ensure\s+each\s+word\s+in\s+your\s+response\s+has\s+at\s+least\s+"
    r"one\s+consonant\s+cluster\s*\(two\s+or\s+more\s+consonants\s+together\)\.",
    flags=re.I,
)

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def norm_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def recover(prompt: str) -> tuple[str, float, dict[str, int]]:
    matches = list(OVERLAP.finditer(prompt))
    assert len(matches) == 1, len(matches)
    percentage = float(matches[0].group("percentage"))
    stripped, overlap_count = OVERLAP.subn(" ", prompt)
    stripped, keyword_count = SENTENCE_KEYWORD.subn(" ", stripped)
    stripped, consonant_count = CONSONANT_CLUSTER.subn(" ", stripped)
    reference = norm_ws(stripped)
    assert reference
    return reference, percentage, {
        "ratio_overlap": overlap_count,
        "sentence_keyword": keyword_count,
        "consonant_cluster": consonant_count,
    }

def main() -> int:
    raw = fetch(IFBENCH_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB, (git_blob_sha(raw), IFBENCH_BLOB)
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]

    ratio_rows = 0
    recovered_exact_normalized = 0
    percentage_exact = 0
    co_constraint_sets: dict[str, int] = {}
    unexpected_co_constraints: list[dict] = []
    failures: list[dict] = []

    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        ratio_rows += 1
        idx = ids.index("ratio:overlap")
        kwargs = list(row.get("kwargs") or [])
        kw = kwargs[idx]
        expected_ref = norm_ws(str(kw.get("reference_text") or ""))
        expected_pct = float(kw.get("percentage"))
        got_ref, got_pct, removed = recover(str(row.get("prompt") or ""))
        co = sorted(x for x in ids if x != "ratio:overlap")
        key = ",".join(co) if co else "NONE"
        co_constraint_sets[key] = co_constraint_sets.get(key, 0) + 1
        if any(x not in {"sentence:keyword", "words:consonants"} for x in co):
            unexpected_co_constraints.append({"key": row.get("key"), "co": co})
        if got_ref == expected_ref:
            recovered_exact_normalized += 1
        else:
            failures.append({
                "key": row.get("key"),
                "kind": "REFERENCE_MISMATCH",
                "expected": expected_ref,
                "got": got_ref,
                "removed": removed,
            })
        if got_pct == expected_pct:
            percentage_exact += 1
        else:
            failures.append({
                "key": row.get("key"),
                "kind": "PERCENTAGE_MISMATCH",
                "expected": expected_pct,
                "got": got_pct,
            })

    expected_sets = {
        "NONE": 5,
        "sentence:keyword": 4,
        "words:consonants": 3,
    }
    assert ratio_rows == 12, ratio_rows
    assert recovered_exact_normalized == 12, failures
    assert percentage_exact == 12, failures
    assert not unexpected_co_constraints, unexpected_co_constraints
    assert co_constraint_sets == expected_sets, (co_constraint_sets, expected_sets)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_VISIBLE_REFERENCE_SEGMENTER_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "source_git_blob": git_blob_sha(raw),
        "public_ifbench_rows": len(rows),
        "ratio_overlap_rows": ratio_rows,
        "normalized_reference_exact_recovery": recovered_exact_normalized,
        "percentage_exact_recovery": percentage_exact,
        "co_constraint_sets": co_constraint_sets,
        "unexpected_co_constraints": unexpected_co_constraints,
        "terminal_cases_consumed": 0,
        "verified_deductions": [
            "VISIBLE_PROMPT_ONLY_SEGMENTATION_RECOVERS_NORMALIZED_REFERENCE_ON_12_OF_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS",
            "VISIBLE_PROMPT_ONLY_SEGMENTATION_RECOVERS_REQUESTED_PERCENTAGE_ON_12_OF_12_ROWS",
            "PINNED_PUBLIC_RATIO_OVERLAP_CO_CONSTRAINTS_ARE_EXHAUSTIVELY_NONE_SENTENCE_KEYWORD_OR_WORDS_CONSONANTS",
            "NO_PUBLIC_ROW_ID_OR_HIDDEN_KWARGS_ARE_REQUIRED_BY_THE_SEGMENTER_AT_RUNTIME",
        ],
        "hard_nonclaims": [
            "NO_FROZEN_TERMINAL_DATASET_EQUIVALENCE",
            "NO_CLAIM_THAT_TERMINAL_RATIO_OVERLAP_CO_CONSTRAINTS_MATCH_PUBLIC_POPULATION_WITHOUT_BINDING",
            "NO_ACCEPTANCE_PROMOTION_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    Path("livebench_visible_reference_segmenter_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
