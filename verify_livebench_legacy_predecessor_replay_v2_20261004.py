from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_legacy_predecessor_replay_v2_20261004"
sys.path.insert(0, str(SUB))

from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (  # noqa: E402
    compile_visible_constraints,
    source_surface,
)

DATA = ROOT / "livebench_instruction_following_predecessor.parquet"
EXPECTED_DATA_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
EXPECTED_ROWS = 200
EXPECTED_V1_BLOB = "e986035ff68b53c0dc7a7eb478f6e3d8882214aa"
EXPECTED_V2_BLOB = "0e7519f4f2b7d40084effc83a5bef814ee7fd487"
EXPECTED_LINEAGE_BLOB = "96d5a1e3ade8a67a97645411142b9153308b68da"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def clean(v):
    if isinstance(v, str):
        s = v.strip()
        if s and s[0] in "[{" and s[-1] in "]}":
            try:
                return clean(json.loads(s))
            except Exception:
                return v
        return v
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items() if x is not None}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    return v

def prompt_from(row):
    turns = clean(row.get("turns"))
    if isinstance(turns, list) and len(turns) == 1 and isinstance(turns[0], str):
        return turns[0]
    if isinstance(turns, str):
        return turns
    for key in ("prompt", "question", "input"):
        if isinstance(row.get(key), str):
            return row[key]
    raise AssertionError(("PROMPT_COLUMN_UNRESOLVED", sorted(row)))

def hidden_ids_from(row):
    ids = clean(row.get("instruction_id_list"))
    assert isinstance(ids, list) and all(isinstance(x, str) for x in ids), ("BAD_IDS", ids)
    assert len(ids) == len(set(ids)), ("DUPLICATE_HIDDEN_IDS", ids)
    return ids

def hidden_kwargs_from(row, n):
    xs = clean(row.get("kwargs"))
    assert isinstance(xs, list) and len(xs) == n, ("BAD_KWARGS", type(xs), xs)
    out = []
    for x in xs:
        x = clean(x)
        if x is None:
            x = {}
        assert isinstance(x, dict), ("BAD_KWARG_ENTRY", x)
        out.append({k: v for k, v in x.items() if v is not None})
    return out

assert git_blob_sha(SUB / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py") == EXPECTED_V1_BLOB
assert git_blob_sha(SUB / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py") == EXPECTED_V2_BLOB
assert git_blob_sha(SUB / "LIVEBENCH_LEGACY_GENERATOR_LINEAGE_BREAKTHROUGH_20261004_V1.json") == EXPECTED_LINEAGE_BLOB
assert hashlib.sha256(DATA.read_bytes()).hexdigest() == EXPECTED_DATA_SHA256

surface = source_surface()
assert surface["recognized_public_type_count"] == 25
assert surface["registered_legacy_type_count"] == 25
assert surface["all_registered_types_covered_by_recognizers"] is True
assert surface["fully_visible_parameter_type_count_under_historical_generator"] == 25
assert surface["parameter_incomplete_type_count_under_historical_generator"] == 0

rows = pq.read_table(DATA).to_pylist()
assert len(rows) == EXPECTED_ROWS, len(rows)

failures = []
instruction_counts = Counter()
for i, row in enumerate(rows):
    prompt = prompt_from(row)
    hidden_ids = hidden_ids_from(row)
    hidden_kwargs = hidden_kwargs_from(row, len(hidden_ids))
    out = compile_visible_constraints(prompt)
    got = out.get("constraints") or []
    got_ids = [x["instruction_id"] for x in got]
    if out.get("status") != "PASS" or not out.get("all_recognized_parameters_complete"):
        failures.append({"row": i, "kind": "COMPILER_NOT_COMPLETE", "out": out})
        continue
    if Counter(got_ids) != Counter(hidden_ids):
        failures.append({"row": i, "kind": "ID_MULTISET_MISMATCH", "expected": hidden_ids, "got": got_ids})
        continue
    got_by_id = {x["instruction_id"]: x for x in got}
    for iid, expected_kwargs in zip(hidden_ids, hidden_kwargs):
        instruction_counts[iid] += 1
        slots = clean(got_by_id[iid].get("slots") or {})
        for key, expected in expected_kwargs.items():
            actual = slots.get(key)
            if key == "prompt_to_repeat" and isinstance(expected, str):
                expected = expected.strip()
            if isinstance(expected, str) and key not in {"prompt_to_repeat"}:
                expected = expected.strip()
            if actual != expected:
                failures.append({
                    "row": i,
                    "kind": "KWARG_MISMATCH",
                    "instruction_id": iid,
                    "key": key,
                    "expected": expected,
                    "actual": actual,
                })

if failures:
    print(json.dumps({"status": "FAIL", "failure_count": len(failures), "sample": failures[:12]}, ensure_ascii=False, indent=2))
    raise SystemExit(1)

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_PREDECESSOR_COMPILER_V2_REPLAY_RECEIPT_V1",
    "status": "PASS",
    "dataset_repository": "livebench/instruction_following",
    "dataset_revision": "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695",
    "dataset_file": "data/test-00000-of-00001.parquet",
    "dataset_sha256": EXPECTED_DATA_SHA256,
    "rows": len(rows),
    "exact_instruction_multiset_recovery_rows": len(rows),
    "score_relevant_hidden_kwarg_recovery_rows": len(rows),
    "observed_instruction_ids": sorted(instruction_counts),
    "observed_instruction_id_count": len(instruction_counts),
    "terminal_active_2024_11_25_prompts_read": 0,
    "acceptance_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
    "hard_nonclaim": "PREDECESSOR_REPLAY_PROVES_HISTORICAL_GENERATOR_FAMILY_RECOVERY_ONLY__ACTIVE_TERMINAL_LINEAGE_STILL_REQUIRES_SEPARATE_PROOF",
}
print(json.dumps(receipt, sort_keys=True))
