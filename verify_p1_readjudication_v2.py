from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.p1_composite_proof_readjudicator_v2 import evaluate

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json": "1da223b8133e83d3ba1b238012593b39dcae91f9",
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py": "0c386e6b78a8e97e9c1944e63600047bc4e2849b",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py": "6e1dfaa6b63fc629d55d07b2361bf625f11a5ce3",
    "canonical/runtime/contract_native_proof_suites.py": "0210790c7dd705ef328e1b55d529a30c5c6c3337",
    "canonical/runtime/p1_composite_proof_readjudicator_v2.py": "4c78106d5cda114f052cf8ef160ba0d172d1bacf",
    "canonical/tests/test_p1_composite_proof_readjudicator_v2.py": "7013994bb52709efe7d3f2a5d60e1ad6fcbf2215",
    "canonical/governance/P1_COMPOSITE_PROOF_READJUDICATION_CANDIDATE_V2.json": "407b3851fda96cedfe8907bb65a76a3c6b92b2d5",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> int:
    errors: list[str] = []
    observed = {}
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"MISSING:{rel}")
            continue
        got = git_blob_sha(path)
        observed[rel] = got
        if got != expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{got}:{expected}")

    result = evaluate()
    if result.get("semantic_repair_complete") is not True:
        errors.append("SEMANTIC_REPAIR_NOT_COMPLETE")
    if result.get("partition_exact") is not True:
        errors.append("PARTITION_NOT_EXACT")
    if result.get("killed_mutation_count") != 9:
        errors.append("NOT_ALL_NINE_MUTATIONS_KILLED")
    if result.get("strict_v4_baseline_failures") != []:
        errors.append("V4_BASELINE_REGRESSION")
    if result.get("terminal_results_replayed") != 0:
        errors.append("TERMINAL_REPLAY_DETECTED")
    if result.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("FRESH_TERMINAL_EVIDENCE_DETECTED")
    if result.get("capability_credit_delta") != 0 or result.get("family_credit_delta") != 0:
        errors.append("PREMATURE_CREDIT_DETECTED")
    if result.get("promotion_authority") is not False:
        errors.append("PREMATURE_PROMOTION_AUTHORITY")

    out = {
        "schema": "PROJECT_BRAIN_P1_COMPOSITE_PROOF_READJUDICATION_PUBLIC_VERIFIER_V2",
        "status": (
            "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_BLOBS__9_OF_9_MUTATIONS_KILLED__ZERO_BASELINE_REGRESSION__ZERO_TERMINAL_REPLAY__ZERO_CREDIT"
            if not errors
            else "FAIL_CLOSED"
        ),
        "errors": errors,
        "exact_blob_count": len(EXPECTED),
        "observed_blobs": observed,
        "readjudication": result,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
