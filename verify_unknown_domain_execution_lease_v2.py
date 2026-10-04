from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RUNTIME_PATH = ROOT / "canonical/runtime/unknown_domain_direct_execution_lease_v1.py"
TEST_PATH = ROOT / "canonical/tests/test_unknown_domain_direct_execution_lease_v1.py"

EXPECTED_BLOBS = {
    str(RUNTIME_PATH.relative_to(ROOT)): "61487ed479e08c3f9f2cd19977e7fe7d2ca0230e",
    str(TEST_PATH.relative_to(ROOT)): "1bb1a6d9fd09dbc3a4673ffeb372bc4b7d57239b",
}
EXPECTED_LEASE_DIGEST = "7e23ef76fd83b58374db8ddfe87c82d109235559a44c9715ca16824f7b43d731"
EXPECTED_GENERATOR_V1_BLOB = "f974a4594c78e74693c7ba5a19f131dfa481b937"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in EXPECTED_BLOBS.items():
    path = ROOT / rel
    assert path.is_file(), rel
    got = git_blob_sha(path)
    assert got == expected, (rel, got, expected)

from canonical.runtime import unknown_domain_direct_execution_lease_v1 as lease
from canonical.tests import test_unknown_domain_direct_execution_lease_v1 as lease_tests

payload = lease.canonical_lease_payload()
serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
assert hashlib.sha256(serialized).hexdigest() == EXPECTED_LEASE_DIGEST
assert lease.lease_digest_sha256() == EXPECTED_LEASE_DIGEST
assert lease.expected_claim_ref() == lease.CLAIM_NAMESPACE + EXPECTED_LEASE_DIGEST
assert payload["exact_execution_subject"]["generator_v1"] == EXPECTED_GENERATOR_V1_BLOB
assert "nonce" not in json.dumps(payload).lower()
assert "timestamp" not in json.dumps(payload).lower()
assert "run_label" not in json.dumps(payload).lower()

ready = lease_tests.ready_state()
out = lease.verify_point_of_use_state(ready)
assert out["ready_for_atomic_claim_only"] is True, out
assert out["claim_ref"] == lease.expected_claim_ref()
assert out["case_generation_authority"] is False
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert out["acceptance_credit"] is False

mutated = lease.canonical_lease_payload()
mutated["exact_execution_subject"] = dict(mutated["exact_execution_subject"])
mutated["exact_execution_subject"]["generator_v1"] = "0" * 40
assert lease.lease_digest_sha256(mutated) != EXPECTED_LEASE_DIGEST
mutated_state = lease_tests.ready_state()
mutated_state["exact_execution_subject"] = dict(mutated_state["exact_execution_subject"])
mutated_state["exact_execution_subject"]["generator_v1"] = "0" * 40
mutated_out = lease.verify_point_of_use_state(mutated_state)
assert mutated_out["ready_for_atomic_claim_only"] is False
assert "EXACT_EXECUTION_SUBJECT_MISMATCH" in mutated_out["reasons"]

suite = unittest.defaultTestLoader.loadTestsFromModule(lease_tests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()

print(json.dumps({
    "status": "INDEPENDENT_STRENGTHENED_EXECUTION_LEASE_PASS",
    "runtime_git_blob_sha": EXPECTED_BLOBS[str(RUNTIME_PATH.relative_to(ROOT))],
    "tests_git_blob_sha": EXPECTED_BLOBS[str(TEST_PATH.relative_to(ROOT))],
    "generator_v1_git_blob_sha": EXPECTED_GENERATOR_V1_BLOB,
    "lease_digest_sha256": EXPECTED_LEASE_DIGEST,
    "claim_ref": lease.expected_claim_ref(),
    "unit_tests_run": result.testsRun,
    "production_cases_generated": 0,
    "terminal_cases_consumed": 0,
    "incremental_spend_usd": 0,
    "execution_authority": False,
    "acceptance_credit": False
}, sort_keys=True))
