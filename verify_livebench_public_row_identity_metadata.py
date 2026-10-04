#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_GIT_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"

HF_URL = "https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet"
HF_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
HF_BYTES = 537024

RELEASE = "2026-06-25"
ACTIVE_RELEASES = {
    "2024-06-24","2024-07-26","2024-08-31","2024-11-25",
    "2025-04-02","2025-04-25","2025-05-30","2025-11-25",
    "2025-12-23","2026-01-08","2026-06-25",
}
ALLOWED_TERMINAL_COLUMNS = {
    "question_id","task","livebench_release_date","livebench_removal_date"
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-metadata-proof"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def date_s(v) -> str:
    return v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)


def trailing_digits(s: str):
    m = re.search(r"(\d+)$", s)
    return m.group(1) if m else None


def terminal_id_shape(s: str) -> str:
    # Replace digit runs so logs expose structure, not a giant ID dump.
    return re.sub(r"\d+", "<N>", s)


def main() -> int:
    ifbench_raw = fetch(IFBENCH_URL)
    assert git_blob_sha(ifbench_raw) == IFBENCH_GIT_BLOB
    public_rows = [
        json.loads(line)
        for line in ifbench_raw.decode("utf-8").splitlines()
        if line.strip()
    ]
    assert len(public_rows) == 300
    public_keys = [str(r["key"]) for r in public_rows]
    assert len(public_keys) == len(set(public_keys))
    public_key_set = set(public_keys)

    hf_raw = fetch(HF_URL)
    assert len(hf_raw) == HF_BYTES
    assert hashlib.sha256(hf_raw).hexdigest() == HF_SHA256
    parquet = Path("/tmp/livebench_if_metadata_only.parquet")
    parquet.write_bytes(hf_raw)

    schema_names = set(pq.read_schema(parquet).names)
    assert ALLOWED_TERMINAL_COLUMNS <= schema_names

    # Critical firewall: only these four metadata columns are loaded.
    table = pq.read_table(parquet, columns=sorted(ALLOWED_TERMINAL_COLUMNS))
    assert set(table.column_names) == ALLOWED_TERMINAL_COLUMNS
    rows = table.to_pylist()
    assert len(rows) == 400

    active = []
    for r in rows:
        rd = date_s(r["livebench_release_date"])
        rem = r["livebench_removal_date"] or ""
        if rd in ACTIVE_RELEASES and (rem == "" or rem > RELEASE):
            active.append(r)

    assert len(active) == 200
    task_counts = Counter(str(r["task"]) for r in active)
    assert task_counts == {
        "paraphrase": 50,
        "simplify": 50,
        "story_generation": 50,
        "summarize": 50,
    }

    qids = [str(r["question_id"]) for r in active]
    assert len(qids) == len(set(qids))

    transforms = {
        "exact": lambda s: s,
        "trailing_digits": trailing_digits,
        "after_last_colon": lambda s: s.rsplit(":", 1)[-1],
        "after_last_slash": lambda s: s.rsplit("/", 1)[-1],
        "after_last_underscore": lambda s: s.rsplit("_", 1)[-1],
        "after_last_hyphen": lambda s: s.rsplit("-", 1)[-1],
    }
    transform_stats = {}
    for name, fn in transforms.items():
        mapped = [fn(q) for q in qids]
        nonnull = [m for m in mapped if m is not None]
        hits = [m for m in nonnull if m in public_key_set]
        transform_stats[name] = {
            "nonnull": len(nonnull),
            "public_key_hits": len(hits),
            "unique_public_key_hits": len(set(hits)),
            "all_200_unique_public_keys": (
                len(hits) == 200 and len(set(hits)) == 200
            ),
        }

    # Safe structural diagnostics only: no prompt/turn/kwargs values.
    shapes = Counter(terminal_id_shape(q) for q in qids)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUBLIC_ROW_IDENTITY_METADATA_DIAGNOSTIC_V1",
        "status": "PASS_METADATA_ONLY_DIAGNOSTIC",
        "source_bindings": {
            "ifbench_git_blob": IFBENCH_GIT_BLOB,
            "hf_sha256": HF_SHA256,
            "hf_bytes": HF_BYTES,
        },
        "terminal_firewall": {
            "loaded_columns": sorted(ALLOWED_TERMINAL_COLUMNS),
            "prompt_loaded": False,
            "turn_loaded": False,
            "kwargs_loaded": False,
            "instruction_id_list_loaded": False,
        },
        "population": {
            "terminal_rows_total": len(rows),
            "terminal_active_rows": len(active),
            "public_ifbench_rows": len(public_rows),
            "task_counts": dict(sorted(task_counts.items())),
        },
        "question_id_shapes": dict(shapes.most_common()),
        "transform_stats": transform_stats,
        "exact_question_id_set_intersection": len(set(qids) & public_key_set),
        "conclusion": (
            "ROW_IDENTITY_METADATA_PROVED"
            if any(v["all_200_unique_public_keys"] for v in transform_stats.values())
            else "NO_SIMPLE_METADATA_KEY_IDENTITY_PROVED"
        ),
        "hard_nonclaims": [
            "NO_TERMINAL_PROMPT_OR_TURN_TEXT_READ",
            "NO_TERMINAL_KWARGS_OR_INSTRUCTION_IDS_READ",
            "NO_SCORE_OR_ACCEPTANCE_CREDIT",
            "NO_CASE_SPECIFIC_REPAIR",
        ],
        "accounting": {
            "terminal_prompt_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "incremental_spend_usd": 0,
        },
    }
    Path("livebench_public_row_identity_metadata_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
