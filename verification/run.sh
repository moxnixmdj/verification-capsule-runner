#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import hashlib
expected={
  "canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v3.py": "2405e79255cdf4f9bc994f083f3bd4a58c9c5298",
  "canonical/tests/test_certificate_gated_selected_route_runtime_entrypoint_v3.py": "b373212e08810cab1e19661709d4f964b8f23f4f",
  "canonical/governance/CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json": "d89793403137d9a72c1876bfdf722421e9313d80",
  "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V3.json": "6572f67b13945830c13c0a78c23ab261feeac016",
  "canonical/runtime/router_deployment_canary_v1.py": "de71202a17071c8af88ec7ac6e1f241fb42854c2",
  "canonical/runtime/symbolic_router_deployment_canary_predicate_v1.py": "b8a9ba97dc4a2e11cfbcf03fb36dcaa5ca0e45e6",
  "canonical/verification/ROUTER_DEPLOYMENT_CANARY_ADEQUACY_CERTIFICATE_20261007_V1.json": "e521f7b75123bca5cc9704340283a727bb45e957",
  "canonical/verification/ROUTER_DEPLOYMENT_CANARY_ADMISSION_CERTIFICATE_20261007_V1.json": "1b2f97e7d46877b8782ea211fd15f679e6bfb5b0",
  "canonical/verification/SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_ADEQUACY_CERTIFICATE_20261007_V1.json": "1f87838111c606437442b5d100f57004faf89a05",
  "canonical/verification/SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_ADMISSION_CERTIFICATE_20261007_V1.json": "5eda5a3275cb11c273159426ab79565d6d2ceaab"
}
for path,want in expected.items():
    data=Path(path).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    assert got==want,(path,want,got)
runtime=Path("canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v3.py").read_text()
assert "CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1.json" not in runtime
assert "CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V2.json" not in runtime
assert "AMBIGUOUS_CERTIFIED_ROUTE_MATCH" in runtime
assert "CURRENT_CERTIFICATE_GATED_SELECTED_ROUTE_REGISTRY.json" in runtime
print("EXACT_PRIVATE_BLOBS_BOUND")
PY
python3 -m pytest -q canonical/tests/test_certificate_gated_selected_route_runtime_entrypoint_v3.py
python3 - <<'PY'
from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v3 as r
p=r.preflight()
assert p["pass"] is True,p
assert p["match_modes"]==["EXACT_CONTEXT_DIGEST","SYMBOLIC_PREDICATE_CALLABLE"],p
print("PASS__CERTIFIED_ROUTE_CURRENT_REGISTRY_V3_ISOLATED_EXECUTION")
PY
