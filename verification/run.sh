#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import hashlib
from pathlib import Path

expected = {
    "verification/canonical/runtime/current_one_shot_projection_v1.py":
        "18ca8958632625c8562e47adca87bfd1d4fdc4b7",
    "verification/canonical/tests/test_current_one_shot_dynamic_admission_pointer_synthetic_v1.py":
        "b2c7988c28f1322c71585a43b9b2985ac4ea1ed4",
}
for rel, want in expected.items():
    raw = Path(rel).read_bytes()
    got = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if got != want:
        raise SystemExit(f"BLOB_MISMATCH:{rel}:{got}:{want}")
print("EXACT_BLOBS_PASS")
PY

PYTHONPATH=verification python -m py_compile \
  verification/canonical/runtime/current_one_shot_projection_v1.py \
  verification/canonical/tests/test_current_one_shot_dynamic_admission_pointer_synthetic_v1.py

PYTHONPATH=verification python -m unittest -v \
  canonical.tests.test_current_one_shot_dynamic_admission_pointer_synthetic_v1

python - <<'PY'
import json
print(json.dumps({
    "status": "PASS__DYNAMIC_ADMISSION_POINTER_TARGET_PROJECTION",
    "runtime_git_blob_sha": "18ca8958632625c8562e47adca87bfd1d4fdc4b7",
    "test_git_blob_sha": "b2c7988c28f1322c71585a43b9b2985ac4ea1ed4",
    "pointer_target_follow_verified": True,
    "stale_snapshot_nonfatal_verified": True,
    "target_blob_tamper_fail_closed_verified": True,
    "namespace_escape_fail_closed_verified": True,
    "terminal_authority": False,
    "terminal_credit_delta": 0,
}, sort_keys=True))
PY
