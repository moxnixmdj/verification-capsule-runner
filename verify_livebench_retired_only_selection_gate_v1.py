#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://datasets-server.huggingface.co"
DATASET = "livebench/instruction_following"
TARGET_DATE = "2026-06-25"
PAGE = 100
EXPECTED_RETIRED = 200
EXPECTED_TASK_COUNTS = {
    "paraphrase": 50,
    "simplify": 50,
    "story_generation": 50,
    "summarize": 50,
}
# Deliberately only a comparison predicate supported by the official HF /filter API.
# SQL NULL does not satisfy <> '', so this excludes both NULL and empty active markers.
WHERE = '"livebench_removal_date"<>'''
SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RETIRED_ONLY_SELECTION_GATE_V1"


class GateError(RuntimeError):
    pass


def get_json(path: str, params: dict[str, object]) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-brain-retired-only-qualification-gate/1"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = response.read()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise GateError("NON_OBJECT_RESPONSE")
    return data


def discover_split() -> tuple[str, str]:
    data = get_json("/splits", {"dataset": DATASET})
    matches = [
        row for row in data.get("splits", [])
        if row.get("dataset") == DATASET
    ]
    # Fail closed rather than silently choosing among multiple configs/splits.
    exact = [
        row for row in matches
        if str(row.get("config")) == "default" and str(row.get("split")) == "test"
    ]
    if len(exact) != 1:
        raise GateError(
            "EXPECTED_EXACT_DEFAULT_TEST_SPLIT:"
            + json.dumps(matches, sort_keys=True)
        )
    return "default", "test"


def fetch_retired_only(config: str, split: str) -> tuple[list[dict], list[int]]:
    rows: list[dict] = []
    returned_row_indices: list[int] = []
    expected_total = None
    offset = 0

    while True:
        data = get_json(
            "/filter",
            {
                "dataset": DATASET,
                "config": config,
                "split": split,
                "where": WHERE,
                "offset": offset,
                "length": PAGE,
            },
        )
        if data.get("partial") is True:
            raise GateError("FILTER_RESULT_PARTIAL")

        page = data.get("rows")
        if not isinstance(page, list):
            raise GateError("ROWS_NOT_LIST")

        total = data.get("num_rows_total")
        if not isinstance(total, int):
            raise GateError("MISSING_NUM_ROWS_TOTAL")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise GateError("FILTER_TOTAL_CHANGED_DURING_PAGINATION")

        for item in page:
            if not isinstance(item, dict) or not isinstance(item.get("row"), dict):
                raise GateError("MALFORMED_ROW_WRAPPER")
            returned_row_indices.append(int(item.get("row_idx")))
            rows.append(item["row"])

        offset += len(page)
        if not page or offset >= expected_total:
            break
        if len(page) > PAGE:
            raise GateError("SERVER_RETURNED_OVERSIZED_PAGE")

    if expected_total != len(rows):
        raise GateError(f"FILTER_TOTAL_MISMATCH:{expected_total}:{len(rows)}")
    return rows, returned_row_indices


def norm_date(value: object) -> str:
    value = "" if value is None else str(value)
    return value[:10]


def main() -> int:
    config, split = discover_split()
    rows, indices = fetch_retired_only(config, split)

    if len(rows) != EXPECTED_RETIRED:
        raise GateError(f"EXPECTED_{EXPECTED_RETIRED}_RETIRED_ROWS_GOT_{len(rows)}")
    if len(set(indices)) != len(indices):
        raise GateError("DUPLICATE_SERVER_ROW_INDEX")

    required = {
        "question_id",
        "task",
        "category",
        "turns",
        "instruction_id_list",
        "kwargs",
        "livebench_release_date",
        "livebench_removal_date",
    }
    tasks = collections.Counter()
    metadata_rows = []
    prompt_hashes = []

    for row in rows:
        missing = sorted(required.difference(row))
        if missing:
            raise GateError("MISSING_REQUIRED_COLUMNS:" + ",".join(missing))
        if row["category"] != "instruction_following":
            raise GateError("NON_IF_CATEGORY")
        removal = norm_date(row["livebench_removal_date"])
        if not removal:
            raise GateError("ACTIVE_OR_EMPTY_REMOVAL_ROW_CROSSED_FIREWALL")
        if removal > TARGET_DATE:
            raise GateError("ROW_NOT_RETIRED_BY_TARGET_DATE:" + removal)
        turns = row["turns"]
        if not isinstance(turns, list) or not turns or not isinstance(turns[0], str):
            raise GateError("INVALID_PROMPT_TURNS")
        # Prompt bytes are intentionally never printed or written. Only a one-way
        # digest is retained so future candidate-response receipts can bind inputs.
        prompt_hashes.append(hashlib.sha256(turns[0].encode("utf-8")).hexdigest())
        task = str(row["task"])
        tasks[task] += 1
        metadata_rows.append({
            "question_id": str(row["question_id"]),
            "task": task,
            "release": norm_date(row["livebench_release_date"]),
            "removal": removal,
            "row_idx": indices[len(metadata_rows)],
        })

    if dict(tasks) != EXPECTED_TASK_COUNTS:
        raise GateError(
            "RETIRED_TASK_GEOMETRY_MISMATCH:"
            + json.dumps(dict(tasks), sort_keys=True)
        )
    if len(set(x["question_id"] for x in metadata_rows)) != EXPECTED_RETIRED:
        raise GateError("DUPLICATE_QUESTION_ID")

    metadata_digest = hashlib.sha256(
        json.dumps(
            sorted(metadata_rows, key=lambda x: x["question_id"]),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    prompt_set_digest = hashlib.sha256(
        "\n".join(sorted(prompt_hashes)).encode("utf-8")
    ).hexdigest()

    receipt = {
        "schema": SCHEMA,
        "status": "PASS",
        "dataset_viewer": {
            "dataset": DATASET,
            "config": config,
            "split": split,
            "endpoint_used_for_prompt_bearing_rows": "/filter",
            "where": WHERE,
            "rows_returned": len(rows),
            "partial": False,
        },
        "retired_population": {
            "target_date": TARGET_DATE,
            "count": len(rows),
            "task_counts": dict(sorted(tasks.items())),
            "unique_question_ids": len({x["question_id"] for x in metadata_rows}),
            "metadata_digest_sha256": metadata_digest,
            "prompt_set_digest_sha256": prompt_set_digest,
        },
        "contamination_firewall": {
            "unfiltered_rows_endpoint_called": False,
            "parquet_downloaded": False,
            "active_prompt_requested": False,
            "active_prompt_logged": False,
            "retired_prompt_logged": False,
            "only_server_filtered_prompt_rows_crossed_process_boundary": True,
            "all_returned_rows_retired_by_target_date": True,
        },
        "qualification_boundary": {
            "candidate_model_executed": False,
            "score_computed": False,
            "purpose": (
                "PREQUALIFICATION_SELECTION_GATE_FOR_MODEL_OR_RUNTIME "
                "BEFORE_ANY_ACTIVE_2026_06_25_TERMINAL_PROMPT_CAN_BE_CONSUMED"
            ),
        },
        "hard_nonclaims": [
            "CURRENT_DATASET_VIEWER_CONTENT_IS_NOT_CLAIMED_BYTE_IDENTICAL_TO_A_HISTORICAL_PINNED_PARQUET",
            "NO_MODEL_CAPABILITY_SCORE_OR_ACCEPTANCE_CREDIT",
            "NO_ACTIVE_2026_06_25_TERMINAL_PROMPT_WAS_REQUESTED_BY_THIS_GATE",
        ],
    }
    out = Path("livebench_retired_only_selection_gate_receipt.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
