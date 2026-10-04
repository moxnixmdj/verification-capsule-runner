from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/unknown_domain_direct_execution_lease_v1.py":"61487ed479e08c3f9f2cd19977e7fe7d2ca0230e",
 "canonical/tests/test_unknown_domain_direct_execution_lease_v1.py":"1bb1a6d9fd09dbc3a4673ffeb372bc4b7d57239b",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_CANDIDATE_V1.json":"8a360a230e956f79507f40fdde8725a401c4a6ae",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
}

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel, expected in EXPECTED.items():
    p=ROOT/rel
    assert p.is_file(), rel
    got=git_blob(p.read_bytes())
    assert got==expected,(rel,got,expected)

candidate=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_CANDIDATE_V1.json").read_text())
assert candidate["status"]=="CANDIDATE__DETERMINISTIC_NONCE_FREE_ONE_USE_LEASE__TRANSITIVE_DEPENDENCY_CLOSED__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CASES__ZERO_CREDIT"
assert candidate["subjects"]["generator_v1_git_blob_sha"]==EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"]
assert candidate["subjects"]["runtime_git_blob_sha"]==EXPECTED["canonical/runtime/unknown_domain_direct_execution_lease_v1.py"]
assert candidate["subjects"]["tests_git_blob_sha"]==EXPECTED["canonical/tests/test_unknown_domain_direct_execution_lease_v1.py"]

proc=subprocess.run(
    [sys.executable,"-m","unittest","canonical.tests.test_unknown_domain_direct_execution_lease_v1","-v"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout)
assert proc.returncode==0,proc.returncode

from canonical.runtime import unknown_domain_direct_execution_lease_v1 as lease
payload=lease.canonical_lease_payload()
assert payload["exact_execution_subject"]["generator_v1"]==EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"]
digest=lease.lease_digest_sha256()
claim_ref=lease.expected_claim_ref()
assert claim_ref=="refs/heads/unknown-domain-direct-claims/"+digest
assert "nonce" not in json.dumps(payload,sort_keys=True).lower()
assert "timestamp" not in json.dumps(payload,sort_keys=True).lower()
assert "run_label" not in json.dumps(payload,sort_keys=True).lower()

print(json.dumps({
 "status":"INDEPENDENT_REPAIRED_EXECUTION_LEASE_PASS",
 "lease_runtime_git_blob_sha":EXPECTED["canonical/runtime/unknown_domain_direct_execution_lease_v1.py"],
 "lease_tests_git_blob_sha":EXPECTED["canonical/tests/test_unknown_domain_direct_execution_lease_v1.py"],
 "lease_candidate_git_blob_sha":EXPECTED["canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_CANDIDATE_V1.json"],
 "generator_v1_git_blob_sha":EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"],
 "lease_digest_sha256":digest,
 "claim_ref":claim_ref,
 "persistent_learned_bytes":0,
 "production_cases_consumed":0
},sort_keys=True))
