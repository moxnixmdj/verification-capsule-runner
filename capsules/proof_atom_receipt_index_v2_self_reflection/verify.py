from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/runtime/proof_atom_receipt_index_v2.py": "710071856e15f1561deb17347e7cf9cb0c477322",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "80f7a5ca4d4a7c35b0997f3e552c0ee23d3a0bfa",
    "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "27fa9deb9ef591adb9e33b24bd8e971a74ef5e89",
}

def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for rel, expected in EXPECTED.items():
    got = git_blob_sha(ROOT / rel)
    assert got == expected, (rel, got, expected)

gov = json.loads((ROOT / "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json").read_text(encoding="utf-8"))
assert gov["runtime_git_blob_sha"] == EXPECTED["canonical/runtime/proof_atom_receipt_index_v2.py"]
assert gov["tests_git_blob_sha"] == EXPECTED["canonical/tests/test_proof_atom_receipt_index_v2.py"]
assert "RECEIPT_INDEX_SELF_VERIFICATION_ARTIFACTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE" in gov["hard_rules"]
assert "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_RESTATEMENTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE" in gov["hard_rules"]
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

subprocess.run(
    [sys.executable, "-m", "unittest", "canonical.tests.test_proof_atom_receipt_index_v2", "-v"],
    cwd=ROOT,
    check=True,
)

print(json.dumps({
    "status": "PASS",
    "exact_brain_blob_count": len(EXPECTED),
    "receipt_index_v2_runtime_blob": EXPECTED["canonical/runtime/proof_atom_receipt_index_v2.py"],
    "receipt_index_v2_tests_blob": EXPECTED["canonical/tests/test_proof_atom_receipt_index_v2.py"],
    "self_verification_quarantine": True,
    "declared_corpus_restatement_quarantine": True,
    "credit_delta": 0,
}, indent=2, sort_keys=True))
