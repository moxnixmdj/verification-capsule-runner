#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import urllib.request
from decimal import Decimal
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
NEW_LIVEBENCH_COMMIT = "caa4253c8a3aa93b5c7ec234e681d4f120a20240"
HF_DATASET_REVISION = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
MODEL = "claude-opus-5-5-max-effort"
IF_TASKS = ["paraphrase", "simplify", "story_generation", "summarize"]

GITHUB_FILES = {
    "judgment_router": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/gen_ground_truth_judgment.py",
        "b36561da5b54380c724c507462d0ee65feefeac8",
    ),
    "legacy_registry": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/instructions_registry.py",
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    ),
    "categories_2026_06_25": (
        f"https://raw.githubusercontent.com/LiveBench/new-livebench/{NEW_LIVEBENCH_COMMIT}/public/categories_2026_06_25.json",
        "50b5672fe14023f5ba14efc1ce16e221e6573056",
    ),
    "table_2026_06_25": (
        f"https://raw.githubusercontent.com/LiveBench/new-livebench/{NEW_LIVEBENCH_COMMIT}/public/table_2026_06_25.csv",
        "73ab7d8d9752b4d7cc1bc8c574ab0eb80c36c84b",
    ),
    "cost_2026_06_25": (
        f"https://raw.githubusercontent.com/LiveBench/new-livebench/{NEW_LIVEBENCH_COMMIT}/public/cost_2026_06_25.csv",
        "6f6271ed5497706e290675a1ad92a716a0f45b6b",
    ),
}

HF_INFO_URL = "https://huggingface.co/api/datasets/livebench/instruction_following"
HF_STATS_URL = (
    "https://datasets-server.huggingface.co/statistics"
    "?dataset=livebench%2Finstruction_following&config=default&split=test"
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-brain-independent-livebench-scope-verifier-v1"},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def fetch_json(url: str) -> dict:
    return json.loads(fetch(url).decode("utf-8"))


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def find_stat(stats: dict, name: str) -> dict:
    for item in stats.get("statistics", []):
        if item.get("column_name") == name:
            return item
    raise AssertionError("STAT_NOT_FOUND:" + name)


def normalize_datetime(value: object) -> str:
    return str(value).replace("T", " ").replace("Z", "").strip()


def find_csv_row(text: str, model: str) -> dict[str, str]:
    rows = csv.DictReader(io.StringIO(text))
    for row in rows:
        if row.get("model") == model:
            return row
    raise AssertionError("MODEL_ROW_NOT_FOUND:" + model)


def count_legacy_registry(source: str) -> int:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in node.targets):
            continue
        assert isinstance(node.value, ast.Dict), "INSTRUCTION_DICT_NOT_LITERAL_DICT"
        return len(node.value.keys)
    raise AssertionError("INSTRUCTION_DICT_NOT_FOUND")


def main() -> int:
    observed_blobs: dict[str, str] = {}
    sources: dict[str, str] = {}
    for key, (url, expected_blob) in GITHUB_FILES.items():
        raw = fetch(url)
        actual_blob = git_blob_sha(raw)
        assert actual_blob == expected_blob, (key, actual_blob, expected_blob)
        observed_blobs[key] = actual_blob
        sources[key] = raw.decode("utf-8")

    # 1. Frozen evaluator routing: every instruction-following question whose
    # release date precedes 2025-11-25 is separated into the legacy batch path.
    router = sources["judgment_router"]
    legacy_predicate = (
        "m.question.get('category') == 'instruction_following' and "
        "m.question.get(\"livebench_release_date\", \"\") < \"2025-11-25\""
    )
    assert legacy_predicate in router
    assert "scores = instruction_following_process_results(" in router
    assert "score = ifbench_process_results(question, llm_answer, debug)" in router

    # 2. Count the load-bearing legacy checker registry structurally.
    legacy_checker_count = count_legacy_registry(sources["legacy_registry"])
    assert legacy_checker_count == 25, legacy_checker_count

    # 3. Bind Hugging Face statistics to the current exact dataset revision,
    # without fetching prompt rows or semantic case content.
    hf_info = fetch_json(HF_INFO_URL)
    observed_hf_sha = str(hf_info.get("sha") or "")
    assert observed_hf_sha == HF_DATASET_REVISION, observed_hf_sha

    stats = fetch_json(HF_STATS_URL)
    assert stats.get("partial") is False
    assert int(stats.get("num_examples")) == 400

    release_stat = find_stat(stats, "livebench_release_date")
    assert release_stat.get("column_type") == "datetime"
    release_cs = release_stat["column_statistics"]
    observed_min = normalize_datetime(release_cs["min"])
    observed_max = normalize_datetime(release_cs["max"])
    assert observed_min.startswith("2024-06-24 00:00:00"), observed_min
    assert observed_max.startswith("2024-11-25 00:00:00"), observed_max
    assert observed_max < "2025-11-25 00:00:00"

    task_stat = find_stat(stats, "task")
    task_cs = task_stat["column_statistics"]
    frequencies = task_cs.get("frequencies") or {}
    assert set(frequencies) == set(IF_TASKS), frequencies
    assert sum(int(v) for v in frequencies.values()) == 400, frequencies

    # 4. Bind the 2026-06-25 leaderboard IF category and exact Opus comparator.
    categories = json.loads(sources["categories_2026_06_25"])
    assert categories.get("IF") == IF_TASKS, categories.get("IF")

    score_row = find_csv_row(sources["table_2026_06_25"], MODEL)
    cost_row = find_csv_row(sources["cost_2026_06_25"], MODEL)

    task_scores = {task: Decimal(score_row[task]) for task in IF_TASKS}
    task_counts = {task: int(cost_row["nq_" + task]) for task in IF_TASKS}
    assert task_counts == {task: 50 for task in IF_TASKS}, task_counts
    total_questions = sum(task_counts.values())
    assert total_questions == 200

    raw_mean = sum(task_scores.values(), Decimal("0")) / Decimal(len(IF_TASKS))
    assert raw_mean == Decimal("65.73775"), raw_mean
    displayed_one_decimal = raw_mean.quantize(Decimal("0.1"))
    assert displayed_one_decimal == Decimal("65.7"), displayed_one_decimal

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_2026_LEGACY_SCOPE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "source_bindings": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "new_livebench_commit": NEW_LIVEBENCH_COMMIT,
            "huggingface_dataset_revision": HF_DATASET_REVISION,
            "source_git_blobs": observed_blobs,
        },
        "verified": [
            "FROZEN_ROUTER_SENDS_PRE_2025_11_25_INSTRUCTION_FOLLOWING_ROWS_TO_LEGACY_BATCH_EVALUATOR",
            "LEGACY_REGISTERED_CHECKER_COUNT_IS_EXACTLY_25",
            "CURRENT_PUBLIC_INSTRUCTION_FOLLOWING_DATASET_REVISION_IS_EXACTLY_PINNED",
            "PUBLIC_DATASET_HAS_400_ROWS_AND_IS_NOT_PARTIAL_IN_STATISTICS",
            "PUBLIC_DATASET_RELEASE_DATE_RANGE_IS_2024_06_24_THROUGH_2024_11_25_AND_ENTIRELY_PRE_ROUTER_CUTOFF",
            "PUBLIC_DATASET_TASK_DOMAIN_IS_EXACTLY_PARAPHRASE_SIMPLIFY_STORY_GENERATION_SUMMARIZE",
            "2026_06_25_LEADERBOARD_IF_CATEGORY_IS_EXACTLY_THE_SAME_FOUR_TASK_NAMES",
            "OPUS_5_5_MAX_EFFORT_HAS_50_QUESTIONS_PER_IF_TASK_AND_200_TOTAL",
            "OPUS_5_5_MAX_EFFORT_RAW_EQUAL_TASK_IF_MEAN_IS_EXACTLY_65_73775_PERCENT",
            "ONE_DECIMAL_DISPLAY_OF_RAW_MEAN_IS_65_7_PERCENT",
        ],
        "architecture_consequence": {
            "public_source_conjunction": (
                "The current public LiveBench instruction-following corpus is wholly on the "
                "legacy side of the frozen evaluator cutoff, while the 2026-06-25 leaderboard "
                "IF scope is the same four task names with 50 questions each. The load-bearing "
                "public scorer grammar for this comparator should therefore be scheduled around "
                "the 25-checker legacy registry, not the 58 modern IFBench checker registry."
            ),
            "checker_surface_before": 83,
            "legacy_checker_surface": 25,
            "modern_checker_surface_removed_from_current_public_critical_path": 58,
            "fraction_removed": 58 / 83,
        },
        "hard_nonclaims": [
            "NO_PROMPT_ROWS_OR_TERMINAL_CASE_SEMANTIC_CONTENT_FETCHED_BY_THIS_VERIFIER",
            "NO_PRIVATE_ROW_IDENTITY_OR_PRIVATE_DATASET_CONTENT_PROOF",
            "NO_CLAIM_SCORE_ONLY_WITNESSES_PROVE_SEMANTIC_PARAPHRASE_SIMPLIFY_SUMMARIZE_OR_STORY_CAPABILITY",
            "NO_LIVEBENCH_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_TERMINAL_CASE_73_OR_LATER_EXPOSURE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_case_semantic_content_consumed": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    Path("livebench_2026_legacy_scope_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
