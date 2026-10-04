#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request
import subprocess
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

HF_URL = "https://huggingface.co/datasets/livebench/instruction_following/resolve/main/data/test-00000-of-00001.parquet"\nHF_REVISION = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
HF_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
HF_BYTES = 537024
LB_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
JUDGMENT_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LB_COMMIT}/livebench/gen_ground_truth_judgment.py"
JUDGMENT_GIT_BLOB = "b36561da5b54380c724c507462d0ee65feefeac8"
DISPATCH_CUTOFF = "2025-11-25"
TARGET_RELEASE = "2026-06-25"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def as_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value or "")

def main() -> int:
    source_raw = fetch(JUDGMENT_URL)
    assert git_blob_sha(source_raw) == JUDGMENT_GIT_BLOB
    source = source_raw.decode("utf-8")
    dispatch_literal = (
        "m.question.get('category') == 'instruction_following' and "
        "m.question.get(\"livebench_release_date\", \"\") < \"2025-11-25\""
    )
    assert dispatch_literal in source
    assert "scores = instruction_following_process_results(if_questions, if_answers, task_name, model_id, debug)" in source
    assert "# IFBench format questions (old format never reaches play_a_match_gt)" in source
    assert "score = ifbench_process_results(question, llm_answer, debug)" in source

    # urllib receives an intermittent Hugging Face 404 on the exact immutable
    # resolve URL although curl against the same pinned object succeeds in the
    # already-verified release-population capsule.  Use curl with redirects and
    # retries, then bind bytes by size+SHA256 before any parquet read.
    path = Path("/tmp/instruction_following.parquet")
    subprocess.run([
        "curl", "--fail", "--location", "--retry", "3", "--silent", "--show-error",
        HF_URL, "-o", str(path)
    ], check=True)
    parquet_raw = path.read_bytes()
    assert len(parquet_raw) == HF_BYTES
    assert hashlib.sha256(parquet_raw).hexdigest() == HF_SHA256

    columns = ["question_id", "task", "category", "livebench_release_date", "livebench_removal_date"]
    rows = pq.read_table(path, columns=columns).to_pylist()
    assert len(rows) == 400
    assert len({row["question_id"] for row in rows}) == 400
    assert all(row["category"] == "instruction_following" for row in rows)

    all_dates = [as_date(row["livebench_release_date"]) for row in rows]
    assert max(all_dates) < DISPATCH_CUTOFF, max(all_dates)

    active = []
    for row in rows:
        removal = as_date(row["livebench_removal_date"])
        if removal == "" or removal > TARGET_RELEASE:
            active.append(row)

    counts = Counter(row["task"] for row in active)
    expected_counts = {
        "paraphrase": 50,
        "simplify": 50,
        "story_generation": 50,
        "summarize": 50,
    }
    assert counts == expected_counts, (counts, expected_counts)
    assert len(active) == 200
    active_dates = [as_date(row["livebench_release_date"]) for row in active]
    assert max(active_dates) < DISPATCH_CUTOFF

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_DISPATCH_COLLAPSE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "pinned_inputs": {
            "livebench_commit": LB_COMMIT,
            "gen_ground_truth_judgment_git_blob_sha": JUDGMENT_GIT_BLOB,
            "hf_revision": HF_REVISION,\n            "hf_transport_ref": "main",\n            "hf_transport_safety": "EXACT_SHA256_AND_BYTE_LENGTH_PIN_CONTENT_IDENTITY_DESPITE_MOVING_TRANSPORT_REF",
            "hf_parquet_sha256": HF_SHA256,
            "hf_parquet_bytes": HF_BYTES,
        },
        "metadata_only_dataset_audit": {
            "rows_total": len(rows),
            "min_release_date": min(all_dates),
            "max_release_date": max(all_dates),
            "active_target_rows": len(active),
            "active_task_counts": dict(sorted(counts.items())),
            "active_min_release_date": min(active_dates),
            "active_max_release_date": max(active_dates),
            "dispatch_cutoff": DISPATCH_CUTOFF,
            "modern_ifbench_active_count": sum(1 for d in active_dates if d >= DISPATCH_CUTOFF),
            "legacy_ifeval_active_count": sum(1 for d in active_dates if d < DISPATCH_CUTOFF),
            "prompt_or_turn_columns_read": False,
        },
        "verified_deductions": [
            "EXACT_FROZEN_400_ROW_DATASET_HAS_NO_INSTRUCTION_FOLLOWING_RELEASE_AT_OR_AFTER_2025_11_25",
            "EXACT_ACTIVE_2026_06_25_TARGET_POPULATION_IS_200_ROWS_50_PER_FOUR_IF_TASKS",
            "ALL_200_ACTIVE_TARGET_ROWS_ENTER_OLD_INSTRUCTION_FOLLOWING_MATCHES",
            "ALL_200_ACTIVE_TARGET_ROWS_USE_LEGACY_INSTRUCTION_FOLLOWING_PROCESS_RESULTS",
            "ZERO_ACTIVE_TARGET_ROWS_USE_MODERN_IFBENCH_PROCESS_RESULTS",
            "MODERN_IFBENCH_58_CHECKER_SUCCESSOR_WORK_IS_NOT_LOAD_BEARING_FOR_THE_FROZEN_2026_06_25_TARGET",
        ],
        "hard_nonclaims": [
            "NO_BRAIN_LIVEBENCH_SCORE_CLAIM",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
            "NO_EXECUTION_OR_PROMOTION_AUTHORITY",
            "NO_UNEXPOSED_TERMINAL_PROMPT_OR_RESPONSE_CONTENT_READ",
            "LEGACY_25_CHECKER_SUCCESSOR_COVERAGE_REMAINS_TO_BE_PROVED_OR_EXECUTED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_cases_exposed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("livebench_legacy_dispatch_collapse_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())