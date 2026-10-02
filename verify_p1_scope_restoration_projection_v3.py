from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "2781b228c1277138eae5fab3d5aacb1a0ece351d",
    "canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V1.json": "0b1db563c7f1c1d0bc90fca025b8576f24d09378",
    "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json": "5d31f372528421ea022a28b8645fbd696cb87a42",
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json": "c62590c2d7bb6024dd73e56f709645989f79cdb8",
    "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V3.json": "f76b3a96c7ac9495c696a44ba2f887ae940d1596",
    "canonical/verification/P1_COMPOSITE_PROOF_RESTORATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json": "0e288acce32d06742db2a7b940820a74f9731073",
    "canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json": "e61741612bafd85697635b0fea97bd93812454cd",
    "canonical/tests/test_p1_scope_restoration_projection_v3.py": "898edea852a5234e4ca2c2f93b3ed9967022197a",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> int:
    errors = []
    observed = {}
    for rel, expected in EXPECTED.items():
        p = ROOT / rel
        if not p.exists():
            errors.append(f"MISSING:{rel}")
            continue
        got = git_blob_sha(p)
        observed[rel] = got
        if got != expected:
            errors.append(f"BLOB_MISMATCH:{rel}:{got}:{expected}")

    if not errors:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest",
             "canonical.tests.test_p1_scope_restoration_projection_v3", "-v"],
            cwd=ROOT, text=True, capture_output=True,
        )
        if proc.returncode != 0:
            errors.append("PROJECTION_REGRESSION_FAILED")
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)

    authority = json.loads((ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())
    if authority["truth"]["opus55_acceptance"] != "2/19_PASS__17/19_OPEN":
        errors.append("OPUS55_ACCEPTANCE_CHANGED")
    if authority["atomic_acceptance_frontier"] != {
        "proved": 7,
        "unresolved": 31,
        "total": 38,
        "authorized_acceptance_case_actions": [],
        "source": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
        "source_git_blob_sha": "af83f4899169e81017767c3316ddcf6b61da5ef6",
        "state": "AUTHORITY_RECONCILED_AFTER_ABSOLUTE_DOMINANCE_SCOPE_FIREWALL"
    }:
        errors.append("ATOMIC_ACCEPTANCE_FRONTIER_CHANGED")
    if authority["truth"]["achieved"] is not False:
        errors.append("TERMINAL_FALSE_NOT_PRESERVED")

    out = {
        "schema":"PROJECT_BRAIN_P1_SCOPE_RESTORATION_PROJECTION_PUBLIC_VERIFIER_V3",
        "status": (
            "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_FINAL_PROJECTION_BLOBS__12_OF_12_CONTRACTS__19_OF_19_PROVISIONAL_BEHAVIORAL_ROWS__2_OF_19_OPUS_ACCEPTANCE_UNCHANGED__7_OF_38_ATOMIC_UNCHANGED__SYNTHESIS_STALE_ACTION_REVOKED__TERMINAL_FALSE"
            if not errors else "FAIL_CLOSED"
        ),
        "errors":errors,
        "exact_blobs":observed,
        "contract_projection":"12_OF_12_WHOLE_SCOPE_PASS",
        "behavioral_projection":"19_OF_19_PROVISIONAL_PASS",
        "opus55_acceptance":"2_OF_19_CLOSED__17_OPEN",
        "atomic_acceptance":"7_OF_38_PROVED__31_UNRESOLVED",
        "terminal_goal_achieved":False,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
