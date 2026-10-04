#!/usr/bin/env python3
from __future__ import annotations

import ast
import datetime
import hashlib
import json
import pathlib
import subprocess
import urllib.request

import pyarrow.parquet as pq

ROOT = pathlib.Path("/tmp/LiveBench")
PINNED_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
SELECTED_LEADERBOARD_RELEASE = "2026-06-25"
CUTOFF = "2025-11-25"

DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
DATASET_ROWS = 400
EXPECTED_SELECTED_ROWS = 200

# Exact release set used by the frozen executor / public loader surface.
VALID_RELEASES = {
    "2024-06-24", "2024-07-26", "2024-08-31", "2024-11-25",
    "2025-04-02", "2025-04-25", "2025-05-30", "2025-11-25",
    "2025-12-23", "2026-01-08", "2026-06-25",
}

EXPECTED_SOURCE_BLOBS = {
    "livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8",
    "livebench/common.py": "95373cc6a82bc935013e2c23d2a183022f802f5c",
    "livebench/process_results/instruction_following/utils.py": "8ce01747887ec0792c8f024e1972e34ece781676",
}


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def source(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("FUNCTION_NOT_FOUND:" + name)


def compact(node: ast.AST) -> str:
    return ast.unparse(node).replace(" ", "").replace("\n", "")


def iso(v) -> str:
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# 1. Bind exact public source bytes.
head = git("rev-parse", "HEAD")
assert head == PINNED_COMMIT, (head, PINNED_COMMIT)
observed_blobs = {
    rel: git("rev-parse", f"HEAD:{rel}") for rel in EXPECTED_SOURCE_BLOBS
}
assert observed_blobs == EXPECTED_SOURCE_BLOBS, {
    "observed": observed_blobs,
    "expected": EXPECTED_SOURCE_BLOBS,
}

# 2. Prove the router compares each match.question release field, not the
# selected leaderboard release passed to load_questions.
router_src = source("livebench/gen_ground_truth_judgment.py")
router = ast.parse(router_src)
gen = function(router, "gen_judgments")
old_assignment = None
for node in ast.walk(gen):
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "old_instruction_following_matches"
    ):
        old_assignment = node.value
        break
assert old_assignment is not None
old_text = compact(old_assignment)
assert "m.question.get('livebench_release_date','')" in old_text or (
    'm.question.get("livebench_release_date","")' in old_text
)
assert "<'2025-11-25'" in old_text or '<"2025-11-25"' in old_text
assert SELECTED_LEADERBOARD_RELEASE not in old_text

# 3. Prove load_questions does not overwrite q.livebench_release_date with the
# selected leaderboard release. The selected release only gates removal_date.
common_src = source("livebench/common.py")
common = ast.parse(common_src)
load_questions = function(common, "load_questions")
load_text = compact(load_questions)
assert "livebench_release" in load_text
assert "livebench_removal_date" in load_text
assert "q['livebench_removal_date']==''" in load_text or (
    'q["livebench_removal_date"]==""' in load_text
)
assert "q['livebench_removal_date']>livebench_release" in load_text or (
    'q["livebench_removal_date"]>livebench_release' in load_text
)
# There must be no assignment that writes the function parameter
# livebench_release into q["livebench_release_date"].
for node in ast.walk(load_questions):
    if isinstance(node, ast.Assign):
        value_text = compact(node.value)
        for target in node.targets:
            target_text = compact(target)
            assert not (
                "livebench_release_date" in target_text
                and value_text == "livebench_release"
            ), "LOADER_OVERWRITES_PER_QUESTION_RELEASE"

# 4. Download the exact frozen dataset and read only routing metadata.
url = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + DATASET_REV
    + "/data/test-00000-of-00001.parquet?download=true"
)
req = urllib.request.Request(
    url, headers={"User-Agent": "project-brain-route-truth-verifier"}
)
with urllib.request.urlopen(req, timeout=60) as response:
    parquet_bytes = response.read()
assert len(parquet_bytes) == DATASET_BYTES
assert sha256(parquet_bytes) == DATASET_SHA256

dataset_path = pathlib.Path("livebench_instruction_following_exact.parquet")
dataset_path.write_bytes(parquet_bytes)
pf = pq.ParquetFile(dataset_path)
assert pf.metadata.num_rows == DATASET_ROWS

table = pq.read_table(
    dataset_path,
    columns=["livebench_release_date", "livebench_removal_date"],
)
release_dates = [iso(v) for v in table.column("livebench_release_date").to_pylist()]
removal_dates = [iso(v) for v in table.column("livebench_removal_date").to_pylist()]
assert len(release_dates) == DATASET_ROWS
assert len(removal_dates) == DATASET_ROWS

selected_dates: list[str] = []
for release_date, removal_date in zip(release_dates, removal_dates):
    if release_date not in VALID_RELEASES:
        continue
    if removal_date and removal_date <= SELECTED_LEADERBOARD_RELEASE:
        continue
    selected_dates.append(release_date)

assert len(selected_dates) == EXPECTED_SELECTED_ROWS, len(selected_dates)
histogram: dict[str, int] = {}
for value in selected_dates:
    histogram[value] = histogram.get(value, 0) + 1
assert histogram == {"2024-11-25": 200}, histogram
assert all(value < CUTOFF for value in selected_dates)

legacy_rows = sum(value < CUTOFF for value in selected_dates)
modern_rows = len(selected_dates) - legacy_rows
assert legacy_rows == 200
assert modern_rows == 0

# 5. Bind the actual old-batch evaluator.
utils_src = source("livebench/process_results/instruction_following/utils.py")
utils = ast.parse(utils_src)
legacy_process = function(utils, "instruction_following_process_results")
legacy_text = compact(legacy_process)
assert "evaluation_main.evaluator(" in legacy_text

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_2026_ROUTE_VARIABLE_TRUTH_INDEPENDENT_VERIFICATION_V2",
    "status": (
        "PASS__EXACT_FROZEN_200_ROUTE_TO_LEGACY_IFEVAL__"
        "IFBENCH58_ROUTE_CANDIDATE_REFUTED"
    ),
    "pinned_commit": PINNED_COMMIT,
    "exact_source_blobs": observed_blobs,
    "selected_leaderboard_release": SELECTED_LEADERBOARD_RELEASE,
    "router_operand": "per-question livebench_release_date",
    "legacy_cutoff": CUTOFF,
    "dataset": {
        "revision": DATASET_REV,
        "sha256": DATASET_SHA256,
        "bytes": DATASET_BYTES,
        "rows": DATASET_ROWS,
    },
    "metadata_only_recomputation": {
        "selected_rows": len(selected_dates),
        "selected_release_histogram": histogram,
        "legacy_ifeval_rows": legacy_rows,
        "modern_ifbench_rows": modern_rows,
        "all_selected_pre_cutoff": True,
    },
    "loader_semantics": {
        "selected_release_overwrites_question_release": False,
        "selected_release_filters_removal_date": True,
    },
    "legacy_processor": (
        "instruction_following_process_results -> "
        "instruction_following_eval.evaluation_main.evaluator"
    ),
    "refuted_proposition": (
        "selected leaderboard release 2026-06-25 >= cutoff therefore "
        "all selected rows use IFBench58"
    ),
    "correct_proposition": (
        "router uses each selected question's livebench_release_date; "
        "all 200 exact selected rows carry 2024-11-25 < cutoff"
    ),
    "terminal_prompt_text_read": False,
    "terminal_response_text_read": False,
    "terminal_kwargs_values_read": False,
    "terminal_instruction_ids_read": False,
    "terminal_case_ids_read": False,
    "terminal_cases_consumed": 0,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
}

out = pathlib.Path("livebench_2026_route_variable_truth_v2_receipt.json")
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
