#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import hashlib
from pathlib import Path
expected={
  "verification/canonical/runtime/one_shot_reality_closure_v2.py":"a3842ba9e5314d250d4dff1b59ac37adbe62882b",
  "verification/canonical/runtime/promote_r2_direct_route_v1.py":"fa6f423837c7f9e8d50d18922f86ca1131c9fa7f",
  "verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py":"e31c0612a905271a5a8e72865afd08cfe13d8cc1",
  "verification/canonical/tests/test_one_shot_r2_route_deployment_contract_v1.py":"167b4f532fd3cda867dd4413e6e869c009be12b6",
}
for rel,want in expected.items():
    raw=Path(rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if got != want:
        raise SystemExit(f"BLOB_MISMATCH:{rel}:{got}:{want}")
print("EXACT_BLOBS_PASS")
PY

PYTHONPATH=verification python -m py_compile \
  verification/canonical/runtime/one_shot_reality_closure_v2.py \
  verification/canonical/runtime/promote_r2_direct_route_v1.py \
  verification/canonical/runtime/r2_direct_route_dynamic_admission_v1.py \
  verification/canonical/tests/test_one_shot_r2_route_deployment_contract_v1.py

cd verification
PYTHONPATH=. python -m unittest -v \
  canonical.tests.test_one_shot_r2_route_deployment_contract_v1

python - <<'PY'
import json
print(json.dumps({
  "status":"PASS__ONE_SHOT_R2_ROUTE_DEPLOYMENT_PROVIDER_CONTRACT",
  "one_shot_git_blob_sha":"a3842ba9e5314d250d4dff1b59ac37adbe62882b",
  "promoter_git_blob_sha":"fa6f423837c7f9e8d50d18922f86ca1131c9fa7f",
  "admission_git_blob_sha":"e31c0612a905271a5a8e72865afd08cfe13d8cc1",
  "test_git_blob_sha":"167b4f532fd3cda867dd4413e6e869c009be12b6",
  "provider_receives_current_noninterference_contract":True,
  "pointer_re_resolved_each_attempt":True,
  "provider_deployment_authority":False,
  "terminal_authority":False,
  "terminal_credit_delta":0
},sort_keys=True))
PY
