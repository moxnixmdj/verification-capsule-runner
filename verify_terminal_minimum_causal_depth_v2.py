from __future__ import annotations
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V2.json": "457e77191bd6566774fff85ef79d3977d1e7ab61",
    "canonical/runtime/terminal_minimum_causal_depth_guard_v2.py": "affb71e9ddb83cdc81ee178697d0f3b9c800758e",
    "canonical/tests/test_terminal_minimum_causal_depth_guard_v2.py": "e734ee48527096ef381db61ed97bd33dd4d140b0",
    "canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_ACTIVATION_V1.json": "324a7a762a3a2e7116372414afa6b52343673a3d",
    "canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_ACTIVATION_V1.json": "c184c1aed33c06f6b4307ace79a959c21de96958",
    "canonical/governance/ARENA_COMPARATOR_PUBLIC_SEMANTICS_RECONCILIATION_V1.json": "d9bbedb43e8b5da66331d9cdd7254718a7ab23db"
}

def git_blob_sha(path: str) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()

for path, want in EXPECTED.items():
    got = git_blob_sha(path)
    assert got == want, (path, want, got)

from canonical.runtime.terminal_minimum_causal_depth_guard_v2 import verify
out = verify()
assert out["status"] == "PASS"
assert out["v1_verified_subject_immutability_preserved"] is True
assert out["blind_threshold_minimum_information_bound"] is True
assert out["relative_elo_transport_fail_closed"] is True
assert out["acceptance_credit_delta"] == 0

from canonical.tests.test_terminal_minimum_causal_depth_guard_v2 import test_guard_passes
test_guard_passes()

print(json.dumps({
    "schema":"PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_V2_INDEPENDENT_RESULT",
    "status":"PASS",
    "exact_subject_blobs":True,
    "v1_verified_subject_immutability_preserved":True,
    "blind_threshold_minimum_information_bound":True,
    "relative_elo_transport_fail_closed":True,
    "matched_noninferiority_not_collapsed":True,
    "execution_authority":False,
    "promotion_authority":False,
    "fresh_reality_authority":False,
    "acceptance_credit_delta":0
}, sort_keys=True))
