#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import hashlib
from pathlib import Path
expected = {
  "verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py":
    "e31c0612a905271a5a8e72865afd08cfe13d8cc1",
  "verification/canonical/runtime/promote_r2_direct_route_v1.py":
    "fa6f423837c7f9e8d50d18922f86ca1131c9fa7f",
  "verification/canonical/tests/test_r2_direct_route_promotion_lease_v1.py":
    "8444048e9728efabf3e47ff06e22038ed997c4ee",
}
for rel,want in expected.items():
    raw=Path(rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if got != want:
        raise SystemExit(f"BLOB_MISMATCH:{rel}:{got}:{want}")
print("EXACT_BLOBS_PASS")
PY

PYTHONPATH=verification python -m py_compile \
  verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py \
  verification/canonical/runtime/promote_r2_direct_route_v1.py \
  verification/canonical/tests/test_r2_direct_route_promotion_lease_v1.py

PYTHONPATH=verification python -m unittest -v \
  canonical.tests.test_r2_direct_route_promotion_lease_v1

python - <<'PY'
import json
print(json.dumps({
  "status":"PASS__R2_DIRECT_ROUTE_NONINTERFERENCE_PROMOTION_GATE",
  "admission_git_blob_sha":"e31c0612a905271a5a8e72865afd08cfe13d8cc1",
  "promoter_git_blob_sha":"fa6f423837c7f9e8d50d18922f86ca1131c9fa7f",
  "test_git_blob_sha":"8444048e9728efabf3e47ff06e22038ed997c4ee",
  "new_route_requires_noninterference_proof":True,
  "stale_noninterference_proof_fail_closed_verified":True,
  "serial_promotion_composition_verified":True,
  "concurrent_promotion_lease_fail_closed_verified":True,
  "exact_repromotion_idempotent_verified":True,
  "terminal_authority":False,
  "terminal_credit_delta":0
},sort_keys=True))
PY
