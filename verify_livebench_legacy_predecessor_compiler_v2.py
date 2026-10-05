#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
import pathlib
import sys
import urllib.request

import pyarrow.parquet as pq

SUBJECT_ROOT = pathlib.Path("subject")
sys.path.insert(0, str(SUBJECT_ROOT.resolve()))
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

DATASET_REV = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
EXPECTED_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
EXPECTED_ROWS = 200
EXPECTED_V1_BLOB = "e986035ff68b53c0dc7a7eb478f6e3d8882214aa"
EXPECTED_V2_BLOB = "0e7519f4f2b7d40084effc83a5bef814ee7fd487"


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [clean(v) for v in value if v is not None]
    return value


def semantically_equal(field: str, expected, actual) -> bool:
    if field == "prompt_to_repeat":
        return str(expected).strip() == str(actual).strip()
    return clean(expected) == clean(actual)


def main() -> None:
    v1_path = SUBJECT_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py"
    v2_path = SUBJECT_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py"
    assert git_blob_sha(v1_path) == EXPECTED_V1_BLOB
    assert git_blob_sha(v2_path) == EXPECTED_V2_BLOB

    url = (
        "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
        f"{DATASET_REV}/data/test-00000-of-00001.parquet?download=true"
    )
    dst = pathlib.Path("legacy_predecessor.parquet")
    urllib.request.urlretrieve(url, dst)
    raw = dst.read_bytes()
    observed_sha = hashlib.sha256(raw).hexdigest()
    assert observed_sha == EXPECTED_SHA256, (observed_sha, EXPECTED_SHA256)

    table = pq.read_table(dst)
    assert table.num_rows == EXPECTED_ROWS, (table.num_rows, EXPECTED_ROWS)
    required = {"turns", "instruction_id_list", "kwargs"}
    assert required.issubset(set(table.column_names)), table.column_names

    rows = table.to_pylist()
    exact_id_rows = 0
    exact_kwarg_rows = 0
    total_instances = 0
    exact_kwarg_instances = 0
    failures = []

    for index, row in enumerate(rows):
        turns = clean(row.get("turns")) or []
        assert isinstance(turns, list) and len(turns) == 1
        prompt = str(turns[0])

        expected_ids = list(clean(row.get("instruction_id_list")) or [])
        expected_kwargs = list(clean(row.get("kwargs")) or [])
        assert len(expected_ids) == len(expected_kwargs)
        total_instances += len(expected_ids)

        out = compiler.compile_visible_constraints(prompt)
        constraints = list(out.get("constraints") or [])
        got_ids = [c.get("instruction_id") for c in constraints]

        ids_ok = (
            out.get("status") == "PASS"
            and Counter(got_ids) == Counter(expected_ids)
            and len(got_ids) == len(expected_ids)
        )
        if ids_ok:
            exact_id_rows += 1

        # The historical conflict registry makes same-family duplicates invalid
        # for this generator lineage. Fail closed if a duplicate appears.
        if len(set(expected_ids)) != len(expected_ids):
            failures.append({
                "row_index": index,
                "kind": "unexpected_duplicate_expected_instruction_id",
                "expected_ids": expected_ids,
            })
            continue

        got_by_id = {c.get("instruction_id"): c for c in constraints}
        row_kwargs_ok = ids_ok
        instance_failures = []

        for iid, expected_raw in zip(expected_ids, expected_kwargs):
            expected = clean(expected_raw or {})
            got = got_by_id.get(iid)
            if got is None:
                row_kwargs_ok = False
                instance_failures.append({"instruction_id": iid, "kind": "missing_constraint"})
                continue

            slots = clean(got.get("slots") or {})
            instance_ok = True
            for field, expected_value in expected.items():
                if field not in slots:
                    instance_ok = False
                    instance_failures.append({
                        "instruction_id": iid,
                        "kind": "missing_slot",
                        "field": field,
                    })
                    continue
                if not semantically_equal(field, expected_value, slots[field]):
                    instance_ok = False
                    instance_failures.append({
                        "instruction_id": iid,
                        "kind": "slot_mismatch",
                        "field": field,
                        "expected": expected_value,
                        "actual": slots[field],
                    })
            if instance_ok:
                exact_kwarg_instances += 1
            else:
                row_kwargs_ok = False

        if row_kwargs_ok:
            exact_kwarg_rows += 1
        else:
            failures.append({
                "row_index": index,
                "kind": "row_mismatch",
                "expected_ids": expected_ids,
                "got_ids": got_ids,
                "details": instance_failures,
            })

    result = {
        "schema": "LIVEBENCH_LEGACY_PREDECESSOR_COMPILER_V2_REPLAY_V1",
        "dataset_revision": DATASET_REV,
        "dataset_sha256": EXPECTED_SHA256,
        "dataset_rows": len(rows),
        "subject_v1_git_blob_sha": EXPECTED_V1_BLOB,
        "subject_v2_git_blob_sha": EXPECTED_V2_BLOB,
        "exact_instruction_multiset_rows": exact_id_rows,
        "exact_kwarg_rows": exact_kwarg_rows,
        "instruction_instances": total_instances,
        "exact_kwarg_instances": exact_kwarg_instances,
        "failed_rows": len(failures),
        "active_terminal_rows_read": 0,
        "active_terminal_prompt_bytes_read": 0,
        "status": (
            "PASS"
            if exact_id_rows == len(rows)
            and exact_kwarg_rows == len(rows)
            and exact_kwarg_instances == total_instances
            and not failures
            else "FAIL"
        ),
        "failures": failures[:25],
    }
    pathlib.Path("verification_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "failures"}, sort_keys=True))
    if result["status"] != "PASS":
        print(json.dumps({"failure_sample": failures[:10]}, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
