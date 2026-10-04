#!/usr/bin/env python3
from __future__ import annotations

import datetime
import hashlib
import importlib
import json
import sys
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

DATA_URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    "0868379c4b5cf62aeacaf8be4f08fced815c81bb/"
    "data/test-00000-of-00001.parquet?download=true"
)
DATA_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATA_BYTES = 537024
FROZEN_RELEASE = "2026-06-25"
VALID_RELEASES = {
    "2024-06-24", "2024-07-26", "2024-08-31", "2024-11-25",
    "2025-04-02", "2025-04-25", "2025-05-30", "2025-11-25",
    "2025-12-23", "2026-01-08", "2026-06-25",
}
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
SOURCE_FILES = {
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}
RAW_PREFIX = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/"
    + LIVEBENCH_COMMIT
    + "/livebench/if_runner/instruction_following_eval/"
)
RECEIPT = Path("livebench_literal_generator_grammar_receipt.json")


def iso(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def normalize_list(v):
    if isinstance(v, str):
        v = json.loads(v)
    if isinstance(v, tuple):
        v = list(v)
    if not isinstance(v, list):
        raise TypeError("LIST_FIELD_TYPE")
    return v


def normalize_kwargs(v):
    if isinstance(v, str):
        v = json.loads(v)
    if not isinstance(v, dict):
        raise TypeError("KWARGS_ITEM_TYPE")
    return {k: value for k, value in v.items() if value is not None}


def write_receipt(out: dict) -> None:
    RECEIPT.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, sort_keys=True))


def main() -> int:
    parquet = Path("frozen_instruction_following.parquet")
    urllib.request.urlretrieve(DATA_URL, parquet)
    if parquet.stat().st_size != DATA_BYTES:
        raise RuntimeError("DATASET_BYTE_SIZE_MISMATCH")
    if sha256_file(parquet) != DATA_SHA256:
        raise RuntimeError("DATASET_SHA256_MISMATCH")

    package = Path("instruction_following_eval")
    package.mkdir(exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    source_verification = {}
    for name, expected_blob in SOURCE_FILES.items():
        data = urllib.request.urlopen(RAW_PREFIX + name, timeout=30).read()
        actual_blob = git_blob_sha(data)
        if actual_blob != expected_blob:
            raise RuntimeError("PINNED_SOURCE_BLOB_MISMATCH")
        (package / name).write_bytes(data)
        source_verification[name] = {
            "git_blob_sha": actual_blob,
            "bytes": len(data),
        }

    sys.path.insert(0, str(Path.cwd()))
    registry = importlib.import_module(
        "instruction_following_eval.instructions_registry"
    )

    cols = [
        "livebench_release_date",
        "livebench_removal_date",
        "category",
        "turns",
        "instruction_id_list",
        "kwargs",
    ]
    rows = pq.read_table(parquet, columns=cols).to_pylist()
    selected = []
    for row in rows:
        release = iso(row.get("livebench_release_date"))
        removal = iso(row.get("livebench_removal_date"))
        if release not in VALID_RELEASES:
            continue
        if removal and removal <= FROZEN_RELEASE:
            continue
        if str(row.get("category") or "") != "instruction_following":
            continue
        selected.append(row)

    if len(rows) != 400:
        raise RuntimeError("RAW_ROW_COUNT_MISMATCH")
    if len(selected) != 200:
        raise RuntimeError("FROZEN_ACTIVE_ROW_COUNT_MISMATCH")

    total_instances = 0
    matched_instances = 0
    all_matched_rows = 0
    rows_with_any_mismatch = 0
    malformed_rows = 0
    unknown_instruction_instances = 0
    reconstruction_error_instances = 0

    for row in selected:
        try:
            turns = normalize_list(row.get("turns"))
            ids = normalize_list(row.get("instruction_id_list"))
            kwargs_list = normalize_list(row.get("kwargs"))
            if not turns or len(ids) != len(kwargs_list):
                malformed_rows += 1
                continue
            prompt = str(turns[0])
        except Exception:
            malformed_rows += 1
            continue

        row_ok = True
        total_instances += len(ids)
        for instruction_id, raw_kwargs in zip(ids, kwargs_list):
            cls = registry.INSTRUCTION_DICT.get(str(instruction_id))
            if cls is None:
                unknown_instruction_instances += 1
                row_ok = False
                continue
            try:
                kwargs = normalize_kwargs(raw_kwargs)
                inst = cls(str(instruction_id))
                descriptor = inst.build_description(**kwargs)
                descriptor = str(descriptor)
            except Exception:
                reconstruction_error_instances += 1
                row_ok = False
                continue
            if descriptor and descriptor in prompt:
                matched_instances += 1
            else:
                row_ok = False

        if row_ok:
            all_matched_rows += 1
        else:
            rows_with_any_mismatch += 1

    pass_condition = (
        len(selected) == 200
        and malformed_rows == 0
        and unknown_instruction_instances == 0
        and reconstruction_error_instances == 0
        and rows_with_any_mismatch == 0
        and all_matched_rows == 200
        and matched_instances == total_instances
        and total_instances > 0
    )

    out = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LITERAL_GENERATOR_GRAMMAR_VERIFICATION_V1",
        "status": (
            "PASS__FROZEN_200_ALL_LEGACY_DESCRIPTORS_LITERAL_IN_PROMPTS"
            if pass_condition
            else "FAIL_CLOSED__FROZEN_LITERAL_DESCRIPTOR_BINDING_NOT_PROVED"
        ),
        "frozen_dataset": {
            "revision": "0868379c4b5cf62aeacaf8be4f08fced815c81bb",
            "parquet_sha256": DATA_SHA256,
            "parquet_bytes": DATA_BYTES,
            "raw_rows": len(rows),
            "active_rows_checked": len(selected),
        },
        "pinned_legacy_source": {
            "repository": "LiveBench/LiveBench",
            "commit": LIVEBENCH_COMMIT,
            "files": source_verification,
        },
        "aggregate_result": {
            "active_rows_checked": len(selected),
            "rows_all_descriptors_literal": all_matched_rows,
            "rows_with_any_mismatch": rows_with_any_mismatch,
            "instruction_instances_checked": total_instances,
            "instruction_instances_literal": matched_instances,
            "malformed_rows": malformed_rows,
            "unknown_instruction_instances": unknown_instruction_instances,
            "reconstruction_error_instances": reconstruction_error_instances,
        },
        "deduction": (
            "THE_FROZEN_200_VISIBLE_CONSTRAINT_SURFACE_IS_LOSSLESSLY_BOUND_TO_"
            "THE_PINNED_LEGACY_build_description_GRAMMAR"
            if pass_condition
            else "NO_LITERAL_GENERATOR_GRAMMAR_BINDING_CREDIT"
        ),
        "firewall": {
            "terminal_prompt_text_emitted": False,
            "terminal_question_ids_emitted": False,
            "terminal_instruction_ids_emitted": False,
            "terminal_kwargs_emitted": False,
            "terminal_responses_read": False,
            "terminal_scorer_feedback_read": False,
            "only_aggregate_counts_emitted": True,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_case_content_exposed": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
        },
        "hard_nonclaim": (
            "A GRAMMAR BINDING DOES NOT PROVE ANY CONSTRUCTED RESPONSE PASSES "
            "THE LEGACY CHECKERS OR THAT THE 65.73775 TARGET IS MET"
        ),
    }
    write_receipt(out)
    return 0 if pass_condition else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        # Never serialize exception text: library errors can contain row values.
        out = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_LITERAL_GENERATOR_GRAMMAR_VERIFICATION_V1",
            "status": "FAIL_CLOSED__VERIFIER_EXCEPTION",
            "error_class": type(exc).__name__,
            "firewall": {
                "terminal_case_content_exposed": False,
                "exception_text_emitted": False,
            },
            "accounting": {
                "incremental_spend_usd": 0,
                "new_terminal_case_content_exposed": 0,
                "acceptance_credit_delta": 0,
            },
        }
        write_receipt(out)
        raise SystemExit(1)
