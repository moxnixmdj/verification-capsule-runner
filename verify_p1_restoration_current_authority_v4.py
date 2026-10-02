from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "564b3261c9630df13705b818d1f346451d9d0ce5",
    "canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V1.json": "0b1db563c7f1c1d0bc90fca025b8576f24d09378",
    "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json": "5d31f372528421ea022a28b8645fbd696cb87a42",
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json": "c62590c2d7bb6024dd73e56f709645989f79cdb8",
    "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V3.json": "f76b3a96c7ac9495c696a44ba2f887ae940d1596",
    "canonical/verification/P1_COMPOSITE_PROOF_RESTORATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json": "0e288acce32d06742db2a7b940820a74f9731073",
    "canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json": "e61741612bafd85697635b0fea97bd93812454cd",
    "canonical/tests/test_p1_scope_restoration_projection_v3.py": "2da3959f61a9f8d7293d3e2c5dbfe89e6bac8697",
    "canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json": "0014c860f7ff11ead76ccfc7073bb7589bdb6159",
    "canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "14496949201835b086b41b10929e3a487468b028",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    observed: dict[str, str] = {}

    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"MISSING:{rel}")
            continue
        got = git_blob_sha(path)
        observed[rel] = got
        if got != expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{got}:{expected}")

    if not errors:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest",
             "canonical.tests.test_p1_scope_restoration_projection_v3", "-v"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            errors.append("P1_PROJECTION_REGRESSION_FAILED")
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)

    authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    projection = load("canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V1.json")
    closure = load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
    matrix = load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
    restore = load("canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V3.json")
    restore_ver = load("canonical/verification/P1_COMPOSITE_PROOF_RESTORATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json")
    synth = load("canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json")
    matched = load("canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json")
    matched_ver = load("canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

    truth = authority.get("truth", {})
    if truth.get("contracts") != "12/12_WHOLE_SCOPE_PASS__P1_COMPOSITE_SCOPE_RESTORED__RAW_TERMINAL_EVIDENCE_PRESERVED":
        errors.append("CONTRACT_PROJECTION_NOT_12_OF_12")
    if truth.get("behavioral_families") != "19/19_PROVISIONAL_BEHAVIORAL_PASS__8_P1_DEPENDENT_ROWS_RESTORED":
        errors.append("BEHAVIORAL_PROJECTION_NOT_19_OF_19")
    if truth.get("opus55_acceptance") != "2/19_PASS__17/19_OPEN":
        errors.append("OPUS55_ACCEPTANCE_CHANGED")
    if truth.get("achieved") is not False:
        errors.append("TERMINAL_FALSE_NOT_PRESERVED")

    atomic = authority.get("atomic_acceptance_frontier", {})
    if (atomic.get("proved"), atomic.get("unresolved"), atomic.get("total")) != (7, 31, 38):
        errors.append("ATOMIC_ACCEPTANCE_CHANGED")
    if atomic.get("authorized_acceptance_case_actions") != []:
        errors.append("FRESH_ACCEPTANCE_CASES_BECAME_AUTHORIZED")

    frontier = authority.get("compiled_next_frontier", {})
    if frontier.get("primary_action_id") == "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA":
        errors.append("EXHAUSTED_SYNTHESIS_ACTION_STILL_PRIMARY")
    if "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA" in frontier.get("available_zero_reality_critical_actions", []):
        errors.append("EXHAUSTED_SYNTHESIS_ACTION_STILL_AVAILABLE")
    if frontier.get("frontier_recompile_required", {}).get("execution_allowed_before_recompile") is not False:
        errors.append("EXECUTION_NOT_FAIL_CLOSED_PENDING_RECOMPILE")
    if synth.get("current_zero_reality_discharge_available") is not False:
        errors.append("SYNTHESIS_EXHAUSTION_NOT_PRESERVED")

    matched_authority = authority.get("authorities", {}).get("matched_scope_hierarchical_refinement", {})
    if matched_authority.get("path") != "canonical/governance/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_ACTIVATION_V1.json":
        errors.append("MATCHED_SCOPE_AUTHORITY_PATH_LOST")
    if not str(matched_authority.get("status", "")).startswith("ACTIVE_INDEPENDENT_PASS"):
        errors.append("MATCHED_SCOPE_AUTHORITY_NOT_ACTIVE")
    if matched_authority.get("verification") != "canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":
        errors.append("MATCHED_SCOPE_VERIFICATION_POINTER_LOST")
    if not str(matched.get("status", "")).startswith("ACTIVE_INDEPENDENT_PASS"):
        errors.append("MATCHED_SCOPE_ACTIVATION_NOT_ACTIVE")
    if not str(matched_ver.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("MATCHED_SCOPE_INDEPENDENT_VERIFICATION_NOT_PRESERVED")
    if "DISCHARGE_TARGET_SPECIFIC_MATCHED_CHILDREN" not in authority.get("next", ""):
        errors.append("TARGET_SPECIFIC_MATCHED_NEXT_PATH_LOST")
    if "P1_WHOLE_SCOPE_RESTORED" not in authority.get("next", ""):
        errors.append("P1_RESTORATION_NOT_REFLECTED_IN_NEXT_PATH")

    if projection["current_truth"]["whole_scope_contracts"] != "12/12_PASS__P1_WHOLE_SCOPE_RESTORED":
        errors.append("PROJECTION_CONTRACT_MISMATCH")
    if projection["current_truth"]["behavioral_families"] != "19/19_PROVISIONAL_BEHAVIORAL_PASS__8_P1_DEPENDENT_ROWS_RESTORED":
        errors.append("PROJECTION_BEHAVIORAL_MISMATCH")
    if projection["current_truth"]["opus55_acceptance"] != "2/19_CLOSED__17/19_OPEN":
        errors.append("PROJECTION_OPUS_MISMATCH")
    if closure.get("behavioral_pass_family_count") != 19 or closure.get("behavioral_quarantined_family_count") != 0:
        errors.append("CLOSURE_BEHAVIORAL_COUNTS_WRONG")
    if closure.get("verified_closed_family_count") != 2 or closure.get("open_family_count") != 17:
        errors.append("CLOSURE_OPUS_COUNTS_WRONG")

    restored_rows = [
        row for row in matrix.get("rows", [])
        if row.get("current_behavioral_scope_state") ==
        "P1_WHOLE_SCOPE_RESTORED__PROVISIONAL_BEHAVIORAL_FAMILY_PASS_REINSTATED"
    ]
    lingering_quarantine = [
        row for row in matrix.get("rows", [])
        if "P1_WHOLE_SCOPE_QUARANTINED" in str(row.get("current_behavioral_scope_state", ""))
    ]
    if len(restored_rows) != 8:
        errors.append(f"RESTORED_ROW_COUNT_NOT_8:{len(restored_rows)}")
    if lingering_quarantine:
        errors.append(f"LINGERING_P1_QUARANTINE_ROWS:{len(lingering_quarantine)}")

    if not str(restore.get("status", "")).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("P1_RESTORATION_ACTIVATION_NOT_ACTIVE")
    if not str(restore_ver.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("P1_RESTORATION_INDEPENDENT_VERIFICATION_NOT_PRESERVED")
    if restore.get("family_credit_delta") != 0 or restore.get("opus55_predicate_credit_delta") != 0:
        errors.append("P1_RESTORATION_PREMATURE_ACCEPTANCE_CREDIT")

    out = {
        "schema": "PROJECT_BRAIN_P1_RESTORATION_CURRENT_AUTHORITY_PUBLIC_VERIFIER_V4",
        "status": (
            "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_CURRENT_AUTHORITY_BLOBS__12_OF_12_CONTRACTS__19_OF_19_PROVISIONAL_BEHAVIORAL_ROWS__2_OF_19_OPUS_ACCEPTANCE_UNCHANGED__7_OF_38_ATOMIC_UNCHANGED__MATCHED_SCOPE_REFINEMENT_PRESERVED__SYNTHESIS_STALE_ACTION_REVOKED__TERMINAL_FALSE"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": errors,
        "exact_blobs": observed,
        "p1_contract_projection": "12_OF_12_WHOLE_SCOPE_PASS",
        "behavioral_projection": "19_OF_19_PROVISIONAL_PASS",
        "opus55_acceptance": "2_OF_19_CLOSED__17_OPEN",
        "atomic_acceptance": "7_OF_38_PROVED__31_UNRESOLVED",
        "matched_scope_hierarchical_refinement_preserved": not errors,
        "terminal_goal_achieved": False,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
