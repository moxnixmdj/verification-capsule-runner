#!/usr/bin/env python3
"""Run the frozen 7,424-case zero-terminal legacy15 exact synthetic audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "livebench_legacy15_joint_historical_replay_v1_20261004"
sys.path.insert(0, str(SUB))

from canonical.runtime.livebench_legacy15_end2end_exact_synthetic_audit_v2 import audit

result = audit(Path("/tmp/livebench"), max_failures=250)
print(json.dumps({
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
