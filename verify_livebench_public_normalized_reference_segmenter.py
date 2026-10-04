#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

IFBENCH_URL = (
    "https://raw.githubusercontent.com/allenai/IFBench/"
    "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
)
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
BRAIN_RUNTIME_BLOB = "8434f82be569474b4d8bf4645163fb79787bc5b4"

FORMAT_CHARS = re.compile(r"[\u200B-\u200D\uFEFF]")
WS = re.compile(r"\s+")
OVERLAP = re.compile(
    r"Maintain a trigram overlap of\s+"
    r"(?P<percentage>\d+(?:\.\d+)?)%\s+"
    r"\(±2%\)\s+with the provided reference text\.",
    re.IGNORECASE,
)
KEYWORD_SENTENCE = re.compile(
    r"The response must include keyword\s+\S+\s+in the\s+"
    r"\d+-(?:st|nd|rd|th)\s+sentence\.",
    re.IGNORECASE,
)
CONSONANT_CLUSTER = re.compile(
    r"Ensure each word in your response has at least one consonant cluster\s+"
    r"\(two or more consonants together\)\.",
    re.IGNORECASE,
)
UNRESOLVED = re.compile(
    r"trigram overlap|provided reference text|"
    r"The response must include keyword|consonant cluster",
    re.IGNORECASE,
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "project-brain-independent-verifier"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def norm(value: str) -> str:
    return WS.sub(" ", FORMAT_CHARS.sub("", str(value or ""))).strip()


def recover_from_visible_prompt_only(prompt: str):
    visible = norm(prompt)
    matches = list(OVERLAP.finditer(visible))
    if len(matches) != 1:
        return None
    percentage = float(matches[0].group("percentage"))
    candidate = OVERLAP.sub(" ", visible)
    candidate = KEYWORD_SENTENCE.sub(" ", candidate)
    candidate = CONSONANT_CLUSTER.sub(" ", candidate)
    candidate = norm(candidate)
    if not candidate or UNRESOLVED.search(candidate):
        return None
    return candidate, percentage


def main() -> int:
    raw = fetch(IFBENCH_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB, (git_blob_sha(raw), IFBENCH_BLOB)
    rows = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 300

    ratio_rows = []
    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        kwargs = list(row.get("kwargs") or [])
        for index, instruction_id in enumerate(ids):
            if instruction_id != "ratio:overlap":
                continue
            assert index < len(kwargs) and isinstance(kwargs[index], dict)
            expected_ref = str(kwargs[index].get("reference_text") or "")
            expected_pct = float(kwargs[index]["percentage"])

            # The constructor sees only the visible prompt. Hidden kwargs are used
            # strictly after recovery as the independent oracle for verification.
            recovered = recover_from_visible_prompt_only(str(row.get("prompt") or ""))
            assert recovered is not None, row.get("key")
            got_ref, got_pct = recovered
            assert got_ref == norm(expected_ref), (
                row.get("key"), got_ref, norm(expected_ref)
            )
            assert got_pct == expected_pct, (row.get("key"), got_pct, expected_pct)
            ratio_rows.append(
                {
                    "key": row.get("key"),
                    "normalized_reference_sha256": hashlib.sha256(
                        got_ref.encode("utf-8")
                    ).hexdigest(),
                    "percentage": got_pct,
                    "prompt_only_recovery_pass": True,
                }
            )

    assert len(ratio_rows) == 12
    assert all(x["prompt_only_recovery_pass"] for x in ratio_rows)

    receipt = {
        "schema": (
            "PROJECT_BRAIN_LIVEBENCH_PUBLIC_NORMALIZED_REFERENCE_"
            "SEGMENTER_INDEPENDENT_VERIFICATION_V1"
        ),
        "status": "PASS",
        "source_git_blobs": {"ifbench_test": git_blob_sha(raw)},
        "bound_brain_runtime_blob": BRAIN_RUNTIME_BLOB,
        "verified": {
            "public_ifbench_rows": len(rows),
            "ratio_overlap_rows": len(ratio_rows),
            "prompt_only_normalized_reference_recovery_passes": len(ratio_rows),
            "prompt_only_percentage_recovery_passes": len(ratio_rows),
            "terminal_cases_consumed": 0,
        },
        "ratio_overlap_rows": ratio_rows,
        "deductions": [
            "PROMPT_ONLY_NORMALIZED_REFERENCE_SEGMENTATION_IS_TOTAL_ON_THE_COMPLETE_PINNED_PUBLIC_RATIO_OVERLAP_POPULATION",
            "THE_SEGMENTER_REQUIRES_NO_PUBLIC_KWARGS_AT_INFERENCE_TIME",
            "PUBLIC_KWARGS_ARE_USED_ONLY_AS_AN_INDEPENDENT_POST_RECOVERY_ORACLE_IN_THIS_VERIFIER",
            "NORMALIZED_REFERENCE_SEGMENTATION_IS_NO_LONGER_THE_PUBLIC_RATIO_OVERLAP_RESIDUAL",
        ],
        "remaining_boundary": [
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_PROOF_THAT_EVERY_UNEXPOSED_TERMINAL_RATIO_OVERLAP_PROMPT_USES_THIS_PUBLIC_CONSTRUCTION_GRAMMAR",
            "NO_TERMINAL_CASE_CONTENT_READ",
            "NO_LIVEBENCH_ACCEPTANCE_EXECUTION_PROMOTION_CAPABILITY_OR_OWNERSHIP_CREDIT",
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
    Path("livebench_public_normalized_reference_segmenter_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
