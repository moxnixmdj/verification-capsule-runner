#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent

DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
DATASET_URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + DATASET_REV
    + "/data/test-00000-of-00001.parquet?download=true"
)

EXECUTOR = ROOT / "execute_livebench_if_replay72_v4_candidate.py"
EXECUTOR_BLOB = "2a57ce896ddbd6819246aab8b44d17a00f36b61e"
MODERN_DISPATCH_CUTOFF = "2025-11-25"
EXPECTED_POPULATION = 200

LEGACY_KWARG_FIELDS = {
    "num_bullets",
    "num_paragraphs",
    "num_words",
    "relation",
    "forbidden_words",
    "section_spliter",
    "num_sections",
    "keywords",
    "end_phrase",
    "postscript_marker",
    "num_sentences",
    "nth_paragraph",
    "first_word",
    "prompt_to_repeat",
}
MODERN_ONLY_SENTINELS = {
    "percentage",
    "small_n",
    "sep",
    "N",
    "word",
    "min_words",
    "max_words",
    "prompt_to_repeat_change",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def date_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    text = str(value)
    return text[:10]


def main() -> int:
    executor_bytes = EXECUTOR.read_bytes()
    executor_blob = git_blob_sha(executor_bytes)
    assert executor_blob == EXECUTOR_BLOB, (executor_blob, EXECUTOR_BLOB)
    executor_text = executor_bytes.decode("utf-8")

    dispatch_literal = 'if release < "2025-11-25":'
    assert dispatch_literal in executor_text
    assert "legacy_eval.test_instruction_following_strict" in executor_text
    assert "ifbench_eval.test_instruction_following_strict" in executor_text

    pop_match = re.search(r"^POPULATION\s*=\s*(\d+)\s*$", executor_text, flags=re.MULTILINE)
    assert pop_match and int(pop_match.group(1)) == EXPECTED_POPULATION

    dst = ROOT / "livebench_frozen_instruction_following.parquet"
    req = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "project-brain-footer-only-dispatch-verifier"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        dst.write_bytes(response.read())

    assert dst.stat().st_size == DATASET_BYTES, (dst.stat().st_size, DATASET_BYTES)
    got_sha = sha256_file(dst)
    assert got_sha == DATASET_SHA256, (got_sha, DATASET_SHA256)

    # IMPORTANT: ParquetFile.metadata and schema_arrow read only file metadata/footer.
    # No row-group data pages or terminal prompt/kwargs values are decoded.
    pf = pq.ParquetFile(dst)
    md = pf.metadata
    assert md.num_rows == 400, md.num_rows

    release_mins = []
    release_maxs = []
    release_column_count = 0
    for rg_index in range(md.num_row_groups):
        rg = md.row_group(rg_index)
        for col_index in range(rg.num_columns):
            col = rg.column(col_index)
            if col.path_in_schema != "livebench_release_date":
                continue
            release_column_count += 1
            stats = col.statistics
            assert stats is not None and stats.has_min_max
            release_mins.append(date_text(stats.min))
            release_maxs.append(date_text(stats.max))

    assert release_column_count == md.num_row_groups, (
        release_column_count,
        md.num_row_groups,
    )
    assert all(release_mins) and all(release_maxs)
    release_min = min(release_mins)
    release_max = max(release_maxs)

    # This is the decisive theorem: the executor dispatch is purely a release-date
    # branch. If the maximum date in the exact frozen parquet is below the cutoff,
    # every row in the full 400-row source, and therefore every row in the selected
    # 200-row terminal population, is forced through the legacy scorer.
    assert release_max < MODERN_DISPATCH_CUTOFF, (
        release_max,
        MODERN_DISPATCH_CUTOFF,
    )

    schema = pf.schema_arrow
    kwargs_field = schema.field("kwargs")
    kwargs_text = str(kwargs_field.type)
    legacy_present = sorted(x for x in LEGACY_KWARG_FIELDS if x in kwargs_text)
    modern_present = sorted(x for x in MODERN_ONLY_SENTINELS if x in kwargs_text)

    # Schema corroboration only; the release-date proof above is authoritative.
    assert len(legacy_present) >= 10
    assert not modern_present, modern_present

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_FROZEN_DATASET_DISPATCH_FAMILY_VERIFICATION_V1",
        "status": "PASS",
        "method": "PINNED_PARQUET_FOOTER_AND_SCHEMA_ONLY__ZERO_ROW_DATA_DECODE",
        "dataset": {
            "revision": DATASET_REV,
            "sha256": got_sha,
            "bytes": dst.stat().st_size,
            "parquet_total_rows": md.num_rows,
            "row_group_count": md.num_row_groups,
            "release_date_footer_min": release_min,
            "release_date_footer_max": release_max,
        },
        "executor": {
            "path": EXECUTOR.name,
            "git_blob_sha": executor_blob,
            "population": EXPECTED_POPULATION,
            "modern_dispatch_cutoff": MODERN_DISPATCH_CUTOFF,
            "dispatch_rule_verified": True,
        },
        "schema_corroboration": {
            "legacy_kwarg_fields_present": legacy_present,
            "modern_only_sentinel_fields_present": modern_present,
        },
        "verified_deductions": [
            "ALL_ROWS_IN_PINNED_400_ROW_SOURCE_PRECEDE_MODERN_IFBENCH_DISPATCH_CUTOFF",
            "ALL_ROWS_IN_FROZEN_200_ROW_SELECTED_POPULATION_ROUTE_TO_LEGACY_IFEVAL_SCORER",
            "MODERN_IFBENCH_58_TYPE_COMPILER_IS_NOT_ON_THE_CRITICAL_PATH_FOR_THIS_FROZEN_ROOT1_PREDICATE",
            "ROOT1_LIVEBENCH_REPAIR_TARGET_REDUCES_TO_25_TYPE_LEGACY_IFEVAL_FAMILY",
        ],
        "hard_nonclaims": [
            "NO_TERMINAL_PROMPT_TEXT_READ",
            "NO_TERMINAL_KWARGS_VALUES_READ",
            "NO_CASE_73_PLUS_EXPOSURE",
            "NO_ACCEPTANCE_OR_PROMOTION_CREDIT",
            "NO_CLAIM_THAT_LEGACY_25_TYPE_SOLVER_ALREADY_PASSES_65_7",
        ],
        "accounting": {
            "terminal_cases_consumed": 0,
            "terminal_rows_decoded": 0,
            "fresh_reality": False,
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
        },
    }

    out = ROOT / "livebench_frozen_dataset_dispatch_family_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
