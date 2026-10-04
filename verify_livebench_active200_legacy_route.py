#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

HF_URL = "https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet"
HF_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
HF_BYTES = 537024
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
JUDGMENT_URL = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/"
    + LIVEBENCH_COMMIT
    + "/livebench/gen_ground_truth_judgment.py"
)
JUDGMENT_BLOB = "b36561da5b54380c724c507462d0ee65feefeac8"
CUTOFF = "2025-11-25"
SELECTED_RELEASE = "2026-06-25"

VALID_RELEASES = {
    "2024-06-24", "2024-07-26", "2024-08-31", "2024-11-25",
    "2025-04-02", "2025-04-25", "2025-05-30", "2025-11-25",
    "2025-12-23", "2026-01-08", "2026-06-25",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def date_string(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def main() -> int:
    parquet = fetch(HF_URL)
    assert len(parquet) == HF_BYTES, (len(parquet), HF_BYTES)
    assert hashlib.sha256(parquet).hexdigest() == HF_SHA256
    Path("/tmp/instruction_following.parquet").write_bytes(parquet)

    judgment_raw = fetch(JUDGMENT_URL)
    assert git_blob_sha(judgment_raw) == JUDGMENT_BLOB
    judgment = judgment_raw.decode("utf-8")

    # Bind the exact per-question dispatch. This is the critical fact:
    # old IF = livebench_release_date < 2025-11-25; those rows are processed
    # with instruction_following_process_results, while newer IF reaches
    # play_a_match_gt -> ifbench_process_results.
    dispatch_literal = (
        "old_instruction_following_matches = [m for m in matches if "
        "m.question.get('category') == 'instruction_following' and "
        "m.question.get(\"livebench_release_date\", \"\") < \"2025-11-25\"]"
    )
    assert dispatch_literal in judgment
    assert "scores = instruction_following_process_results(if_questions, if_answers, task_name, model_id, debug)" in judgment
    assert "score = ifbench_process_results(question, llm_answer, debug)" in judgment

    # Install pyarrow only in the public runner. Read metadata columns only.
    subprocess.run(
        ["python", "-m", "pip", "install", "--quiet", "pyarrow==21.0.0"],
        check=True,
    )
    import pyarrow.parquet as pq

    cols = ["question_id", "task", "livebench_release_date", "livebench_removal_date"]
    table = pq.read_table("/tmp/instruction_following.parquet", columns=cols)
    rows = table.to_pylist()
    assert len(rows) == 400
    assert len({r["question_id"] for r in rows}) == 400

    active = []
    for r in rows:
        release = date_string(r["livebench_release_date"])
        removal = r["livebench_removal_date"] or ""
        if release in VALID_RELEASES and (removal == "" or removal > SELECTED_RELEASE):
            active.append({**r, "release": release})

    assert len(active) == 200
    task_counts = Counter(r["task"] for r in active)
    assert task_counts == {
        "paraphrase": 50,
        "simplify": 50,
        "story_generation": 50,
        "summarize": 50,
    }

    release_counts = Counter(r["release"] for r in active)
    max_release = max(release_counts)
    min_release = min(release_counts)
    modern_count = sum(r["release"] >= CUTOFF for r in active)
    legacy_count = sum(r["release"] < CUTOFF for r in active)

    assert legacy_count == 200
    assert modern_count == 0
    assert max_release < CUTOFF

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_ACTIVE200_LEGACY_ROUTE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "source_bindings": {
            "hf_revision": "0868379c4b5cf62aeacaf8be4f08fced815c81bb",
            "hf_parquet_sha256": hashlib.sha256(parquet).hexdigest(),
            "hf_parquet_bytes": len(parquet),
            "livebench_commit": LIVEBENCH_COMMIT,
            "gen_ground_truth_judgment_git_blob_sha": git_blob_sha(judgment_raw),
        },
        "metadata_only_columns_read": cols,
        "prompt_or_turn_text_read": False,
        "kwargs_or_instruction_ids_read": False,
        "rows_total": len(rows),
        "active_2026_06_25_rows": len(active),
        "active_task_counts": dict(sorted(task_counts.items())),
        "active_release_counts": dict(sorted(release_counts.items())),
        "active_min_release": min_release,
        "active_max_release": max_release,
        "dispatch_cutoff": CUTOFF,
        "active_legacy_ifeval_rows": legacy_count,
        "active_modern_ifbench_rows": modern_count,
        "verified_deductions": [
            "ALL_200_ACTIVE_2026_06_25_INSTRUCTION_FOLLOWING_ROWS_PREDATE_2025_11_25",
            "PINNED_LIVEBENCH_EVALUATOR_ROUTES_ALL_200_ACTIVE_ROWS_TO_LEGACY_INSTRUCTION_FOLLOWING_PROCESS_RESULTS",
            "PINNED_LIVEBENCH_EVALUATOR_ROUTES_ZERO_ACTIVE_ROWS_TO_MODERN_IFBENCH_PROCESS_RESULTS",
            "MODERN_IFBENCH_58_CHECKER_ROUTE_IS_NOT_ON_THE_EXACT_ACTIVE_200_CASE_SCORING_PATH",
        ],
        "hard_nonclaims": [
            "NO_PROMPT_OR_TURN_TEXT_READ",
            "NO_KWARGS_OR_INSTRUCTION_ID_LIST_READ",
            "NO_BRAIN_SCORE_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_FRESH_TERMINAL_REALITY",
        ],
    }
    Path("livebench_active200_legacy_route_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
