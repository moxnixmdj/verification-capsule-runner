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
  "verification/canonical/tests/test_one_shot_auto_direct_route_promotion_v1.py":"10a31678c2b54405e3866bb59ab3be7498f101fd",
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
  verification/canonical/tests/test_one_shot_r2_route_deployment_contract_v1.py \
  verification/canonical/tests/test_one_shot_auto_direct_route_promotion_v1.py

python - <<'PY'
import hashlib, json
from pathlib import Path
root=Path("verification")
gov=root/"canonical/governance"
runtime=root/"canonical/runtime"
gov.mkdir(parents=True,exist_ok=True)
runtime.mkdir(parents=True,exist_ok=True)
wrapper=runtime/"r2_direct_live_admission_v1.py"
wrapper.write_text("# synthetic live wrapper for capsule root\n",encoding="utf-8")
manifest_rel="canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_CAPSULE_EMPTY.json"
manifest=root/manifest_rel
value={
  "schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
  "date":"2026-10-10",
  "status":"ACTIVE_DYNAMIC_ADMISSIONS__EMPTY_BASELINE",
  "selection_class":"UNIQUE_MATCH_REQUIRED",
  "collision_policy":"FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
  "admissions":[],
  "admission_count":0,
  "incremental_spend_usd":0,
  "terminal_authority":False,
  "terminal_credit_delta":0,
}
manifest.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raw=manifest.read_bytes()
sha=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
pointer={
  "schema":"PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_POINTER_V1",
  "date":"2026-10-10",
  "status":"ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
  "binding_semantics":"MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
  "target":{
    "path":manifest_rel,
    "git_blob_sha":sha,
    "schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
  },
  "incremental_spend_usd":0,
  "terminal_authority":False,
  "terminal_credit_delta":0,
}
(gov/"CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json").write_text(
  json.dumps(pointer,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print("SYNTHETIC_LIVE_FRONTIER_READY")
PY

cd verification
PYTHONPATH=. python -m unittest -v \
  canonical.tests.test_one_shot_r2_route_deployment_contract_v1 \
  canonical.tests.test_one_shot_auto_direct_route_promotion_v1

python - <<'PY'
import json
print(json.dumps({
  "status":"PASS__ONE_SHOT_R2_ROUTE_DEPLOYMENT_PROVIDER_CONTRACT_AND_PROMOTION_REGRESSION",
  "one_shot_git_blob_sha":"a3842ba9e5314d250d4dff1b59ac37adbe62882b",
  "promoter_git_blob_sha":"fa6f423837c7f9e8d50d18922f86ca1131c9fa7f",
  "admission_git_blob_sha":"e31c0612a905271a5a8e72865afd08cfe13d8cc1",
  "provider_contract_test_git_blob_sha":"167b4f532fd3cda867dd4413e6e869c009be12b6",
  "promotion_regression_test_git_blob_sha":"10a31678c2b54405e3866bb59ab3be7498f101fd",
  "provider_receives_current_noninterference_contract":True,
  "pointer_re_resolved_each_attempt":True,
  "existing_one_shot_promotion_behavior_preserved":True,
  "provider_deployment_authority":False,
  "terminal_authority":False,
  "terminal_credit_delta":0
},sort_keys=True))
PY
