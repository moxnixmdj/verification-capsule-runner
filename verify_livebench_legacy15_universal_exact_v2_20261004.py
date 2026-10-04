#!/usr/bin/env python3
"""Run the frozen 7,424-case zero-terminal legacy15 exact synthetic audit."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Critical-path subject: parameter-aware exact router, not the superseded
# historical-replay snapshot.
SUB = ROOT / "subject" / "livebench_legacy15_exact_router_v1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py": "34f4df9f0bd265fc555686bd251a264e446d4c04",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py": "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "canonical/runtime/livebench_legacy15_joint_witness_v1.py": "7c53741cb40c51aad5303097b020cb7684d2dcc3",
    "canonical/runtime/livebench_legacy15_general_composer_v1.py": "af42fccbf9275014818fd4cbd1e0fdf05219d4ff",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_end2end_exact_synthetic_audit_v2.py": "b0376cb1e791af6abeb9536e41797b321bb7f7cb",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

actual_blobs = {rel: git_blob_sha(SUB / rel) for rel in EXPECTED_BLOBS}
assert actual_blobs == EXPECTED_BLOBS, {
    "error": "PROOF_SUBJECT_BLOB_DRIFT",
    "expected": EXPECTED_BLOBS,
    "actual": actual_blobs,
}

sys.path.insert(0, str(SUB))
from canonical.runtime.livebench_legacy15_end2end_exact_synthetic_audit_v2 import audit

result = audit(Path("/tmp/livebench"), max_failures=250)
print(json.dumps({
    "proof_subject_blobs": actual_blobs,
    "schema": result["schema"],
    "status": result["status"],
    "scope": result["scope"],
    "results": result["results"],
    "by_archetype": result["by_archetype"],
    "by_profile": result["by_profile"],
    "by_size": result["by_size"],
    "runtime_errors": result["runtime_errors"],
    "exact_failed_instruction_ids": result["exact_failed_instruction_ids"],
    "failure_samples": result["failure_samples"][:50],
}, ensure_ascii=False, sort_keys=True))
assert result["scope"]["synthetic_cases"] == 7424
assert result["scope"]["terminal_rows_read"] == 0
assert result["scope"]["terminal_prompts_read"] == 0
assert result["scope"]["terminal_scores_read"] == 0
assert result["status"] == "PASS__ALL_SYNTHETIC_ACTIVE15_CASES_EXACT_FULL_SCORE"
