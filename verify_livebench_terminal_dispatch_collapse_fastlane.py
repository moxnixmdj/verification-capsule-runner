#!/usr/bin/env python3
from __future__ import annotations

import ast
import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

EXECUTOR = Path("execute_livebench_if_replay72_v4_candidate.py")
EXECUTOR_BLOB = "2a57ce896ddbd6819246aab8b44d17a00f36b61e"
DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
FROZEN_RELEASE = "2026-06-25"
DISPATCH_CUTOFF = "2025-11-25"
POPULATION = 200
VALID_RELEASES = {
    "2024-07-26", "2024-06-24", "2024-08-31", "2024-11-25",
    "2025-04-02", "2025-04-25", "2025-05-30", "2025-11-25",
    "2025-12-23", "2026-01-08", "2026-06-25",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            out = ast.get_source_segment(source, node)
            if out:
                return out
    raise AssertionError(f"FUNCTION_NOT_FOUND:{name}")

def iso(v) -> str:
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]

def main() -> int:
    raw_executor = EXECUTOR.read_bytes()
    assert git_blob_sha(raw_executor) == EXECUTOR_BLOB
    source = raw_executor.decode("utf-8")
    for literal in [
        f'DATASET_REV = "{DATASET_REV}"',
        f'DATASET_SHA256 = "{DATASET_SHA256}"',
        f"DATASET_BYTES = {DATASET_BYTES}",
        f'FROZEN_RELEASE = "{FROZEN_RELEASE}"',
        f"POPULATION = {POPULATION}",
    ]:
        assert literal in source, literal

    case_score = function_source(source, "case_score")
    assert f'if release < "{DISPATCH_CUTOFF}":' in case_score
    assert "legacy_eval.InputExample" in case_score
    assert "ifbench_eval.InputExample" in case_score

    parse_population = function_source(source, "parse_population")
    assert "assert len(sel)==200" in parse_population
    assert 'q["livebench_release_date"] not in valid' in parse_population
    assert "rem and rem <= release" in parse_population

    url = (
        "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
        + DATASET_REV
        + "/data/test-00000-of-00001.parquet?download=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        parquet_bytes = r.read()
    assert len(parquet_bytes) == DATASET_BYTES
    assert sha256(parquet_bytes) == DATASET_SHA256

    path = Path("livebench_instruction_following_exact.parquet")
    path.write_bytes(parquet_bytes)
    table = pq.read_table(path, columns=["livebench_release_date", "livebench_removal_date"])
    release_dates = [iso(v) for v in table.column("livebench_release_date").to_pylist()]
    removal_dates = [iso(v) for v in table.column("livebench_removal_date").to_pylist()]
    assert len(release_dates) == 400
    assert len(removal_dates) == 400

    selected_dates = []
    for rel, rem in zip(release_dates, removal_dates):
        if rel not in VALID_RELEASES:
            continue
        if rem and rem <= FROZEN_RELEASE:
            continue
        selected_dates.append(rel)

    assert len(selected_dates) == POPULATION
    assert max(selected_dates) == "2024-11-25"
    assert all(rel < DISPATCH_CUTOFF for rel in selected_dates)

    schema_text = str(pq.ParquetFile(path).schema_arrow.field("kwargs").type)
    assert "percentage" not in schema_text
    assert "reference_text" not in schema_text

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_TERMINAL_DISPATCH_COLLAPSE_FASTLANE_VERIFICATION_V1",
        "status": "PASS",
        "frozen_executor": {
            "path": str(EXECUTOR),
            "git_blob_sha": EXECUTOR_BLOB,
            "dataset_revision": DATASET_REV,
            "dataset_sha256": DATASET_SHA256,
            "dataset_bytes": DATASET_BYTES,
            "frozen_release": FROZEN_RELEASE,
            "population": POPULATION,
            "dispatch_cutoff": DISPATCH_CUTOFF,
        },
        "metadata_only_recomputation": {
            "source_rows": len(release_dates),
            "selected_rows": len(selected_dates),
            "selected_release_date_min": min(selected_dates),
            "selected_release_date_max": max(selected_dates),
            "all_selected_pre_ifbench_cutoff": True,
            "kwargs_schema_contains_percentage": False,
            "kwargs_schema_contains_reference_text": False,
            "semantic_case_fields_loaded": False,
        },
        "verified": [
            "EXACT_FROZEN_EXECUTOR_AND_DATASET_BINDING_MATCH",
            "FROZEN_POPULATION_SELECTION_YIELDS_EXACTLY_200_ROWS",
            "ALL_200_SELECTED_ROWS_DISPATCH_TO_LEGACY_IFEVAL",
            "MODERN_58_CHECKER_IFBENCH_BRANCH_IS_UNREACHABLE_FOR_THIS_FROZEN_TERMINAL_SUBJECT",
            "RATIO_OVERLAP_IS_NOT_A_REACHABLE_TERMINAL_CHECKER",
        ],
        "hard_nonclaims": [
            "NO_TERMINAL_PROMPTS_RESPONSES_CASE_IDS_OR_KWARGS_VALUES_READ",
            "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_CLAIM_LEGACY_25_CHECKER_GAP_IS_ALREADY_REPAIRED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_semantic_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("livebench_terminal_dispatch_collapse_fastlane_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
