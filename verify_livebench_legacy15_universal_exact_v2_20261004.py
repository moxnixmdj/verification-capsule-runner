#!/usr/bin/env python3
"""Run the frozen 7,424-case zero-terminal legacy15 exact synthetic audit."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_legacy15_joint_historical_replay_v1_20261004"
sys.path.insert(0, str(SUB))

EXPECTED_JOINT_WITNESS_BLOB = "029d6018fd705fa5d1a53c88c4c3dd60764d8489"
JOINT_WITNESS_PATH = SUB / "canonical/runtime/livebench_legacy15_joint_witness_v1.py"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

actual_joint_witness_blob = git_blob_sha(JOINT_WITNESS_PATH)
assert actual_joint_witness_blob == EXPECTED_JOINT_WITNESS_BLOB, (actual_joint_witness_blob, EXPECTED_JOINT_WITNESS_BLOB)

from canonical.runtime.livebench_legacy15_end2end_exact_synthetic_audit_v2 import audit

result = audit(Path("/tmp/livebench"), max_failures=250)
print(json.dumps({
    "schema": result["schema"],
    "current_brain_joint_witness_blob": actual_joint_witness_blob,
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
