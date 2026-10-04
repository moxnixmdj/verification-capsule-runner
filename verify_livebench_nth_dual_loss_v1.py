#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_nth_dual_loss_20261005"
BRAIN_SUBJECT_COMMIT = "0565db760375961935b843df6c3e4b68c58a0e51"
OUTPUT = ROOT / "livebench_nth_dual_loss_independent_verification.json"

EXPECTED_BLOBS = {
    "canonical/governance/LIVEBENCH_NTH_DUAL_LOSS_CLOSURE_PRECOMMIT_20261005_V1.json":
        "73ec772d04fa5c3f06f92909a90c22def194e53e",
    "canonical/runtime/livebench_legacy15_nth_dual_loss_closure_v1.py":
        "2a05e4084e2a5dd17a31726efae56a1de86a7c18",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def main() -> int:
    observed = {}
    for rel, expected in EXPECTED_BLOBS.items():
        got = git_blob_sha(SUBJECT / rel)
        if got != expected:
            raise AssertionError((rel, got, expected))
        observed[rel] = got

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_legacy15_nth_dual_loss_closure_v1 as closure

    try:
        result = closure.audit("/tmp/livebench")
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_NTH_DUAL_LOSS_INDEPENDENT_VERIFICATION_V1",
            "status": (
                "PASS__INDEPENDENT_CONTENT_BOUND_92160_EXACT_POINTWISE_CASES__ZERO_CREDIT"
                if result["status"]
                == "PASS__92160_NTH_DUAL_LOSS_QUOTIENT_CASES_EXACT_POINTWISE_CLOSED"
                and result["coverage"]["cases"] == 92160
                and result["coverage"]["pointwise_exact_max_match"] == 92160
                and result["failure_count"] == 0
                else "FAIL_CLOSED__SUBJECT_RETURNED_COUNTEREXAMPLE_OR_COVERAGE_GAP"
            ),
            "brain_subject_commit": BRAIN_SUBJECT_COMMIT,
            "subject_blobs": observed,
            "subject_status": result["status"],
            "coverage": result["coverage"],
            "failure_count": result["failure_count"],
            "failures_retained": result.get("failures_retained", []),
            "terminal_rows_read": result["terminal_rows_read"],
            "terminal_kwargs_read": result["terminal_kwargs_read"],
            "target_scores_read": result["target_scores_read"],
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_NTH_DUAL_LOSS_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL_CLOSED__VERIFIER_EXCEPTION",
            "brain_subject_commit": BRAIN_SUBJECT_COMMIT,
            "subject_blobs": observed,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "acceptance_credit_delta": 0,
        }
        OUTPUT.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(receipt, sort_keys=True))
        raise

    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": receipt["status"],
        "subject_status": receipt["subject_status"],
        "cases": receipt["coverage"]["cases"],
        "pointwise_exact_max_match":
            receipt["coverage"]["pointwise_exact_max_match"],
        "failure_count": receipt["failure_count"],
    }, sort_keys=True))

    if not receipt["status"].startswith("PASS__"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
