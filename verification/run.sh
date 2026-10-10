#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import hashlib
from pathlib import Path

expected = {
    "verification/canonical/runtime/promote_r2_direct_route_v1.py":
        "6a1a200da6e049553b6c7bca80d2012eaa13c86e",
    "verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py":
        "65fc5bdb5283944d058c6c6a2ff1fe360aa17489",
    "verification/canonical/tests/test_r2_direct_route_promotion_lease_v1.py":
        "229dd6cbf4a75cec28cce575dfef67bb2ec66b54",
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
  verification/canonical/runtime/promote_r2_direct_route_v1.py \
  verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py \
  verification/canonical/tests/test_r2_direct_route_promotion_lease_v1.py

PYTHONPATH=verification python -m unittest -v \
  canonical.tests.test_r2_direct_route_promotion_lease_v1

python - <<'PY'
import json
print(json.dumps({
    "status": "PASS__R2_DIRECT_ROUTE_PROMOTION_CONCURRENCY_GUARD",
    "promoter_git_blob_sha": "6a1a200da6e049553b6c7bca80d2012eaa13c86e",
    "admission_git_blob_sha": "65fc5bdb5283944d058c6c6a2ff1fe360aa17489",
    "test_git_blob_sha": "229dd6cbf4a75cec28cce575dfef67bb2ec66b54",
    "concurrent_lease_contention_fail_closed_verified": True,
    "serial_promotions_compose_without_lost_update_verified": True,
    "exact_repromotion_idempotent_verified": True,
    "terminal_authority": False,
    "terminal_credit_delta": 0,
}, sort_keys=True))
PY
