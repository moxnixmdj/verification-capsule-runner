from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json": "bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
    "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V2.json": "a99ffadcdbef32beb89c2ff86ee4534800f8e19e",
    "canonical/verification/P1_COMPOSITE_PROOF_READJUDICATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json": "ab14aaeb780adc6af9f3b28a2e11cce99ae09cba",
    "canonical/tests/test_p1_composite_proof_restoration_activation_v2.py": "88cc7a0f8c429b891bca90ae74f37a2fd91ff88c",
}


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> int:
    errors = []
    observed = {}
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"MISSING:{rel}")
            continue
        got = blob_sha(path)
        observed[rel] = got
        if got != expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{got}:{expected}")

    if not errors:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest",
             "canonical.tests.test_p1_composite_proof_restoration_activation_v2", "-v"],
            cwd=ROOT, text=True, capture_output=True,
        )
        if proc.returncode != 0:
            errors.append("RESTORATION_ACTIVATION_TEST_FAILED")
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)

    act = json.loads((ROOT / "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V2.json").read_text())
    raw = json.loads((ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json").read_text())
    if act["proof_join"]["complete_required_check_count"] != 8:
        errors.append("CHECK_COUNT_NOT_8")
    if act["proof_join"]["complete_required_mutation_count"] != 9:
        errors.append("MUTATION_COUNT_NOT_9")
    if act["proof_join"]["predeclared_v4_role"]["strict_readjudication_failures"] != 0:
        errors.append("V4_BASELINE_REGRESSION")
    if act["proof_join"]["predeclared_v4_role"]["assigned_mutations_killed"] != 6:
        errors.append("V4_MUTATION_KILL_COUNT_NOT_6")
    if act["proof_join"]["frozen_terminal_role"]["assigned_mutations_killed"] != 3:
        errors.append("TERMINAL_MUTATION_KILL_COUNT_NOT_3")

    rows = raw["reduction_input"]["wave"]["parent_portfolio_receipts"]
    for p in ("T0", "T2"):
        matches = [x for x in rows[p] if x.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"]
        if len(matches) != 1:
            errors.append(f"{p}_P1_RECEIPT_COUNT_NOT_1")
            continue
        row = matches[0]
        if row.get("binding_blob") != "8703c6aa08227467a619a7ae90d0d61f8e54da39":
            errors.append(f"{p}_BINDING_BLOB_DRIFT")
        if not row.get("direct_instrumentation_pass") or not row.get("parent_terminal_acceptance_pass"):
            errors.append(f"{p}_TERMINAL_PASS_MISSING")
        if row.get("case_replaced") or row.get("tuning_replay") or row.get("result_to_runtime_feedback"):
            errors.append(f"{p}_CONTAMINATION_GUARD_FAILED")

    if act.get("opus55_predicate_credit_delta") != 0 or act.get("family_credit_delta") != 0:
        errors.append("PREMATURE_OPUS_CREDIT")
    if act["quarantine_disposition_candidate"]["P1_WITNESS_TRANSPORT_INTO_RECOVERY_ACCEPTANCE"] != "REMAINS_SEPARATE__NO_AUTOMATIC_TRANSPORT":
        errors.append("RECOVERY_TRANSPORT_BOUNDARY_LOST")

    out = {
        "schema":"PROJECT_BRAIN_P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_PUBLIC_VERIFIER_V2",
        "status": (
            "INDEPENDENT_PUBLIC_RUNNER_PASS__WHOLE_P1_COMPOSITE_PROOF_JOIN_VALID__T0_T2_EXACT_RECEIPTS__9_OF_9_MUTATIONS__ZERO_TERMINAL_REPLAY__ZERO_OPUS_CREDIT"
            if not errors else "FAIL_CLOSED"
        ),
        "errors":errors,
        "exact_blobs":observed,
        "whole_p1_contract_restoration_admissible": not errors,
        "postwave_12_of_12_contract_projection_admissible": not errors,
        "automatic_opus55_acceptance_credit": False,
        "terminal_results_replayed":0,
        "fresh_terminal_evidence_consumed":0,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
