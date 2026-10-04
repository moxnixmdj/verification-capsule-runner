#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_sentence_wrapper_closure_20261005"
RUNTIME = SUBJECT / "canonical/runtime"

EXPECTED_BLOBS = {
    "livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "livebench_legacy15_sentence_wrapper_closure_v1.py":
        "a4d83e0963df023273218382fe77cf7a5f9f7822",
}
OUT = ROOT / "livebench_composer_v2_verification.json"


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def write(payload: dict) -> None:
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    actual = {
        name: git_blob_sha(RUNTIME / name)
        for name in EXPECTED_BLOBS
    }
    mismatches = {
        name: {"expected": EXPECTED_BLOBS[name], "actual": actual[name]}
        for name in EXPECTED_BLOBS
        if actual[name] != EXPECTED_BLOBS[name]
    }
    if mismatches:
        write({
            "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL__SUBJECT_BLOB_MISMATCH",
            "mismatches": mismatches,
        })
        raise SystemExit("SUBJECT_BLOB_MISMATCH")

    sys.path.insert(0, str(SUBJECT))
    try:
        from canonical.runtime import (
            livebench_legacy15_sentence_wrapper_closure_v1 as closure,
        )
        result = closure.audit("/tmp/LiveBench")
    except Exception as exc:
        payload = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL__VERIFIER_EXCEPTION",
            "subject_blobs": actual,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }
        write(payload)
        raise

    passed = (
        result.get("status")
        == "PASS__2880_SENTENCE_WRAPPER_CASES_EXACT_POINTWISE_CLOSED"
        and result.get("failure_count") == 0
        and result.get("coverage", {}).get("cases") == 2880
        and result.get("coverage", {}).get("pointwise_exact_max_match") == 2880
    )
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_WRAPPER_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__INDEPENDENT_2880_SENTENCE_WRAPPER_POINTWISE_CLOSURE"
            if passed
            else "FAIL__INDEPENDENT_SENTENCE_WRAPPER_COUNTEREXAMPLE"
        ),
        "subject_blobs": actual,
        "exact_result": result,
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }
    write(receipt)
    print(json.dumps({
        "status": receipt["status"],
        "closure_status": result.get("status"),
        "coverage": result.get("coverage"),
        "failure_count": result.get("failure_count"),
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    rc = main()
    if rc:
        raise SystemExit(rc)
    import verify_livebench_punkt_context_v1 as punkt_verify
    raise SystemExit(punkt_verify.main())
