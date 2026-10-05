#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

PRED_REV = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
PRED_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PRED_ROWS = 200
PRED_URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + PRED_REV + "/data/test-00000-of-00001.parquet"
)
V1_BLOB = "e986035ff68b53c0dc7a7eb478f6e3d8882214aa"
V2_BLOB = "0e7519f4f2b7d40084effc83a5bef814ee7fd487"

HERE = Path(__file__).resolve().parent
CAPSULE = HERE
BRAIN_ROOT = CAPSULE / "brain"
V1_PATH = BRAIN_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py"
V2_PATH = BRAIN_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py"
OUT = Path(os.environ.get("RECEIPT_PATH", str(CAPSULE / "receipt.json")))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-predecessor-replay-v1"})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def norm_value(key: str, value):
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        return [norm_value(key, x) for x in value]
    if isinstance(value, dict):
        return {str(k): norm_value(str(k), v) for k, v in value.items()}
    if key in {"first_word", "letter"} and isinstance(value, str):
        return value.lower()
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def prompt_from_row(row: dict) -> str:
    if "turns" in row:
        turns = row["turns"]
        if isinstance(turns, (list, tuple)) and turns:
            first = turns[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("content", "text", "value"):
                    if isinstance(first.get(key), str):
                        return first[key]
    for key in ("prompt", "question", "instruction"):
        if isinstance(row.get(key), str):
            return row[key]
    raise AssertionError("NO_VISIBLE_PROMPT_COLUMN")


def expected_pairs(row: dict):
    ids = list(row.get("instruction_id_list") or [])
    kwargs = list(row.get("kwargs") or [])
    assert len(ids) == len(kwargs), ("ID_KWARGS_LENGTH_MISMATCH", len(ids), len(kwargs))
    return [(str(iid), dict(kw or {})) for iid, kw in zip(ids, kwargs)]


def main() -> int:
    assert git_blob_sha(V1_PATH) == V1_BLOB, git_blob_sha(V1_PATH)
    assert git_blob_sha(V2_PATH) == V2_BLOB, git_blob_sha(V2_PATH)

    parquet = Path("/tmp/livebench-if-predecessor.parquet")
    download(PRED_URL, parquet)
    actual_sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
    assert actual_sha == PRED_SHA256, (actual_sha, PRED_SHA256)

    import pyarrow.parquet as pq

    pf = pq.ParquetFile(parquet)
    schema_names = set(pf.schema_arrow.names)
    required = {"instruction_id_list", "kwargs"}
    assert required.issubset(schema_names), sorted(schema_names)
    prompt_col = "turns" if "turns" in schema_names else ("prompt" if "prompt" in schema_names else None)
    assert prompt_col is not None, sorted(schema_names)

    table = pq.read_table(parquet, columns=[prompt_col, "instruction_id_list", "kwargs"])
    rows = table.to_pylist()
    assert len(rows) == PRED_ROWS, len(rows)

    sys.path.insert(0, str(BRAIN_ROOT))
    from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as subject

    instruction_multiset = Counter()
    row_failures = []
    rows_exact_ids = 0
    rows_exact_kwargs = 0
    total_constraints = 0

    for idx, row in enumerate(rows):
        prompt = prompt_from_row(row)
        pairs = expected_pairs(row)
        expected_ids = [iid for iid, _ in pairs]
        expected_by_id = {iid: kw for iid, kw in pairs}
        assert len(expected_by_id) == len(pairs), ("DUPLICATE_EXPECTED_ID", idx, expected_ids)

        out = subject.compile_visible_constraints(prompt)
        actual_constraints = list(out.get("constraints") or [])
        actual_ids = [str(c.get("instruction_id")) for c in actual_constraints]
        actual_by_id = {str(c.get("instruction_id")): c for c in actual_constraints}

        ids_ok = Counter(actual_ids) == Counter(expected_ids)
        kwargs_ok = ids_ok
        mismatch = []

        if ids_ok:
            rows_exact_ids += 1
            for iid, expected_kw in pairs:
                c = actual_by_id[iid]
                if not c.get("parameter_complete"):
                    kwargs_ok = False
                    mismatch.append({"iid": iid, "reason": "PARAMETER_INCOMPLETE"})
                    continue
                slots = dict(c.get("slots") or {})
                for key, expected in expected_kw.items():
                    if expected is None:
                        continue
                    av = norm_value(key, slots.get(key))
                    ev = norm_value(key, expected)
                    if av != ev:
                        kwargs_ok = False
                        mismatch.append({
                            "iid": iid,
                            "key": key,
                            "expected": ev,
                            "actual": av,
                        })
        else:
            mismatch.append({
                "reason": "ID_MULTISET_MISMATCH",
                "expected_ids": expected_ids,
                "actual_ids": actual_ids,
            })

        if kwargs_ok:
            rows_exact_kwargs += 1
        else:
            row_failures.append({"row_index": idx, "mismatch": mismatch[:8]})

        instruction_multiset.update(expected_ids)
        total_constraints += len(expected_ids)

    assert rows_exact_ids == PRED_ROWS, ("ID_RECOVERY_FAIL", rows_exact_ids, row_failures[:5])
    assert rows_exact_kwargs == PRED_ROWS, ("KWARG_RECOVERY_FAIL", rows_exact_kwargs, row_failures[:5])
    assert len(instruction_multiset) == 25, ("TYPE_COVERAGE_NOT_25", len(instruction_multiset), sorted(instruction_multiset))

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_PREDECESSOR_COMPILER_V2_INDEPENDENT_REPLAY_V1",
        "status": "PASS",
        "subject": {
            "v1_git_blob_sha": V1_BLOB,
            "v2_git_blob_sha": V2_BLOB,
        },
        "predecessor": {
            "hf_revision": PRED_REV,
            "parquet_sha256": PRED_SHA256,
            "rows": PRED_ROWS,
            "active_terminal_revision_read": False,
        },
        "result": {
            "rows_exact_instruction_id_multiset": rows_exact_ids,
            "rows_exact_score_relevant_kwargs": rows_exact_kwargs,
            "total_constraints": total_constraints,
            "distinct_instruction_types": len(instruction_multiset),
            "instruction_type_counts": dict(sorted(instruction_multiset.items())),
            "all_recognized_parameters_complete": True,
        },
        "proved": [
            "COMPILER_V2_RECOGNIZES_THE_EXACT_LEGACY_INSTRUCTION_MULTISET_ON_ALL_200_HISTORICAL_PREDECESSOR_ROWS",
            "COMPILER_V2_RECOVERS_EVERY_NON_NULL_SCORE_RELEVANT_KWARG_ON_ALL_200_HISTORICAL_PREDECESSOR_ROWS",
            "ALL_25_LEGACY_REGISTERED_INSTRUCTION_TYPES_ARE_EXERCISED_BY_THE_PREDECESSOR_REPLAY",
            "NO_ACTIVE_FROZEN_2024_11_25_TERMINAL_ROW_WAS_READ",
        ],
        "hard_nonclaims": [
            "NO_BYTE_LEVEL_PROOF_THAT_ACTIVE_2024_11_25_PROMPTS_USE_IDENTICAL_DESCRIPTION_TEXT",
            "NO_ACTIVE_TERMINAL_SCORE",
            "NO_ACCEPTANCE_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_FRESH_TERMINAL_REALITY",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "active_terminal_rows_read": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "rows": PRED_ROWS,
        "rows_exact_ids": rows_exact_ids,
        "rows_exact_kwargs": rows_exact_kwargs,
        "distinct_instruction_types": len(instruction_multiset),
        "total_constraints": total_constraints,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
