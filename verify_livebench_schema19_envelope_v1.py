#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import urllib.request

import pyarrow.parquet as pq

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_schema19_20261005"
sys.path.insert(0, str(SUBJECT))

from canonical.runtime import livebench_frozen_schema19_envelope_v1 as envelope
from canonical.runtime import livebench_release_schema_scope_bridge_v1 as schema_bridge

URL = "https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet?download=true"
PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
PARQUET_BYTES = 537024
EXPECTED_BLOBS = {
    "canonical/runtime/livebench_union25_archetypes_v1.py": "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a",
    "canonical/runtime/livebench_release_schema_scope_bridge_v1.py": "fa90615507b048894b5dc118e0c6c39cb2146fcf",
    "canonical/runtime/livebench_frozen_schema19_envelope_v1.py": "8259959828398e7b1415e305fd9bbd8ca308dfc5",
}

def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def main() -> int:
    observed_blobs = {rel: git_blob(SUBJECT / rel) for rel in EXPECTED_BLOBS}
    assert observed_blobs == EXPECTED_BLOBS, (observed_blobs, EXPECTED_BLOBS)

    parquet = ROOT / "schema19_frozen.parquet"
    urllib.request.urlretrieve(URL, parquet)
    raw = parquet.read_bytes()
    assert len(raw) == PARQUET_BYTES
    assert hashlib.sha256(raw).hexdigest() == PARQUET_SHA256

    # Schema-only read. No row group, column values, instruction IDs, kwargs
    # values, prompts, responses, or scores are materialized.
    pf = pq.ParquetFile(parquet)
    arrow_schema = pf.schema_arrow
    kwargs_field = arrow_schema.field("kwargs")
    kwargs_type = kwargs_field.type
    observed_fields = frozenset(kwargs_type.names)
    expected_fields = schema_bridge.EXPECTED_KWARGS_FIELDS
    assert observed_fields == expected_fields, {
        "observed": sorted(observed_fields),
        "expected": sorted(expected_fields),
    }

    out = envelope.verify()
    assert out["envelope_family_count"] == 19
    assert out["compatible_by_cardinality"] == {1: 19, 2: 108, 3: 391, 4: 958, 5: 1632}
    assert out["compatible_total"] == 3108
    assert out["embedded_active15_total"] == 928
    assert out["extra_bearing_total"] == 2180
    assert out["distinct_remaining_extra_signatures"] == 6
    assert out["reduction"]["compatible_sets_deleted"] == 11451
    assert out["reduction"]["extra_signatures_deleted"] == 150

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_FROZEN_SCHEMA19_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_FROZEN_PARQUET_SCHEMA_ONLY__ASSUMPTION_FREE_SCHEMA19__3108_STRUCTURES__SIX_EXTRA_SIGNATURES__ZERO_TERMINAL_CONTENT__ZERO_CREDIT",
        "exact_subject_blobs": observed_blobs,
        "frozen_dataset": {
            "revision": schema_bridge.FROZEN_HF_REVISION,
            "parquet_sha256": PARQUET_SHA256,
            "parquet_bytes": PARQUET_BYTES,
        },
        "schema_only_verification": {
            "kwargs_field_names": sorted(observed_fields),
            "row_values_read": False,
            "instruction_ids_read": False,
            "kwargs_values_read": False,
            "prompts_or_turns_read": False,
            "responses_read": False,
            "scores_read": False,
        },
        "verified_reduction": {
            "registry25_family_count": 25,
            "schema19_family_count": out["envelope_family_count"],
            "registry25_compatible_total": 14559,
            "schema19_compatible_total": out["compatible_total"],
            "compatible_sets_deleted": out["reduction"]["compatible_sets_deleted"],
            "union25_extra_signatures": 156,
            "schema19_extra_signatures": out["distinct_remaining_extra_signatures"],
            "extra_signatures_deleted": out["reduction"]["extra_signatures_deleted"],
            "remaining_extra_signatures": out["remaining_extra_signatures"],
        },
        "assumption_boundary": out["assumption_boundary"],
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_PROVE_THE_SIX_REMAINING_SIGNATURES",
            "THIS_RECEIPT_DOES_NOT_SELF_PROMOTE_LIVEBENCH_ACCEPTANCE",
        ],
    }
    path = ROOT / "livebench_schema19_independent_receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
