#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

DATASET_REV = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
PARQUET_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PARQUET_BYTES = 277319
ROWS = 200
URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + DATASET_REV
    + "/data/test-00000-of-00001.parquet?download=true"
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (  # noqa: E402
    compile_visible_constraints,
)

RECEIPT = HERE / "livebench_legacy_predecessor_replay_receipt_v1.json"


def clean_expected(kwargs: dict) -> dict:
    return {k: v for k, v in (kwargs or {}).items() if v is not None}


def norm_value(key: str, value):
    if key == "prompt_to_repeat" and isinstance(value, str):
        return value.strip()
    return value


def main() -> int:
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_PREDECESSOR_REPLAY_RECEIPT_V1",
        "dataset": {
            "revision": DATASET_REV,
            "sha256": PARQUET_SHA256,
            "bytes": PARQUET_BYTES,
            "expected_rows": ROWS,
        },
        "compiler": {
            "v1_git_blob": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
            "v2_git_blob": "0e7519f4f2b7d40084effc83a5bef814ee7fd487",
        },
        "status": "FAIL_CLOSED",
        "rows_checked": 0,
        "instruction_id_exact_rows": 0,
        "score_relevant_kwarg_exact_rows": 0,
        "all_recognized_parameters_complete_rows": 0,
        "mismatch_count": 0,
        "mismatches": [],
        "terminal_active_rows_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "HISTORICAL_PREDECESSOR_REPLAY_ONLY",
            "NO_ACTIVE_2024_11_25_TERMINAL_PROMPT_READ",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
            "NO_SEMANTIC_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "PREDECESSOR_SUCCESS_DOES_NOT_BY_ITSELF_PROVE_ACTIVE_2024_11_25_BYTE_LEVEL_LINEAGE",
        ],
    }

    try:
        data_path = HERE / "predecessor.parquet"
        urllib.request.urlretrieve(URL, data_path)
        raw = data_path.read_bytes()
        actual_sha = hashlib.sha256(raw).hexdigest()
        receipt["dataset"]["observed_bytes"] = len(raw)
        receipt["dataset"]["observed_sha256"] = actual_sha
        if len(raw) != PARQUET_BYTES or actual_sha != PARQUET_SHA256:
            raise RuntimeError("PINNED_PARQUET_IDENTITY_MISMATCH")

        import pyarrow.parquet as pq

        table = pq.read_table(data_path)
        rows = table.to_pylist()
        if len(rows) != ROWS:
            raise RuntimeError(f"ROW_COUNT_MISMATCH:{len(rows)}")

        for idx, row in enumerate(rows):
            turns = row.get("turns")
            expected_ids = list(row.get("instruction_id_list") or [])
            expected_kwargs = list(row.get("kwargs") or [])
            if not isinstance(turns, list) or len(turns) != 1 or not isinstance(turns[0], str):
                raise RuntimeError(f"ROW_{idx}_TURN_SHAPE")
            if len(expected_ids) != len(expected_kwargs):
                raise RuntimeError(f"ROW_{idx}_ID_KWARG_LENGTH_MISMATCH")

            out = compile_visible_constraints(turns[0])
            got_constraints = list(out.get("constraints") or [])
            got_ids = [c.get("instruction_id") for c in got_constraints]

            ids_ok = got_ids == expected_ids
            complete_ok = bool(out.get("all_recognized_parameters_complete")) and len(got_constraints) == len(expected_ids)

            kw_ok = len(got_constraints) == len(expected_kwargs)
            kw_failures = []
            if kw_ok:
                for j, (constraint, expected_raw) in enumerate(zip(got_constraints, expected_kwargs)):
                    slots = dict(constraint.get("slots") or {})
                    expected = clean_expected(expected_raw)
                    for key, exp in expected.items():
                        if key not in slots:
                            kw_ok = False
                            kw_failures.append({"position": j, "key": key, "reason": "MISSING"})
                            continue
                        got = slots[key]
                        if norm_value(key, got) != norm_value(key, exp):
                            kw_ok = False
                            kw_failures.append({"position": j, "key": key, "reason": "VALUE_MISMATCH"})

            receipt["rows_checked"] += 1
            receipt["instruction_id_exact_rows"] += int(ids_ok)
            receipt["score_relevant_kwarg_exact_rows"] += int(kw_ok)
            receipt["all_recognized_parameters_complete_rows"] += int(complete_ok)

            if not (ids_ok and kw_ok and complete_ok):
                receipt["mismatch_count"] += 1
                if len(receipt["mismatches"]) < 25:
                    receipt["mismatches"].append({
                        "row_index": idx,
                        "expected_instruction_ids": expected_ids,
                        "recovered_instruction_ids": got_ids,
                        "ids_exact": ids_ok,
                        "kwargs_exact": kw_ok,
                        "parameter_complete": complete_ok,
                        "kwarg_failures": kw_failures[:20],
                    })

        passed = (
            receipt["rows_checked"] == ROWS
            and receipt["instruction_id_exact_rows"] == ROWS
            and receipt["score_relevant_kwarg_exact_rows"] == ROWS
            and receipt["all_recognized_parameters_complete_rows"] == ROWS
            and receipt["mismatch_count"] == 0
        )
        receipt["status"] = (
            "PASS__200_OF_200_HISTORICAL_VISIBLE_PROMPTS_EXACTLY_RECOVERED"
            if passed
            else "FAIL__PREDECESSOR_REPLAY_MISMATCH"
        )
        return_code = 0 if passed else 3
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}:{exc}"
        return_code = 4
    finally:
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
