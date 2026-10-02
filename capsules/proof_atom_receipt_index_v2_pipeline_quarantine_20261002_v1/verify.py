from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/proof_atom_receipt_index_v2.py": "5f11b47dc27bfb019bef13cf64a0ef25d7ba1a1f",
    "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
    "canonical/tests/test_proof_atom_receipt_index_v2.py": "14103ef7c96330a281367409a5b76a0a74e7129d",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "7168f55492135d1cf5a865c27f564126db8746f7",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

for rel, expected in EXPECTED.items():
    got = git_blob_sha(ROOT / rel)
    assert got == expected, (rel, got, expected)

gov = load("canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json")
assert gov["runtime_git_blob_sha"] == EXPECTED["canonical/runtime/proof_atom_receipt_index_v2.py"]
assert gov["tests_git_blob_sha"] == EXPECTED["canonical/tests/test_proof_atom_receipt_index_v2.py"]
assert gov["source_basis"]["runtime_git_blob_sha"] == EXPECTED["canonical/runtime/canonical_proof_atom_basis_v2.py"]
assert gov["source_basis"]["frontier_git_blob_sha"] == EXPECTED["canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"]
assert gov["source_basis"]["refinement_overlay_git_blob_sha"] == EXPECTED["canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"]
for rule in [
    "RECEIPT_INDEX_SELF_VERIFICATION_ARTIFACTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE",
    "DECLARED_CONTENT_ADDRESSED_EVIDENCE_CORPUS_RESTATEMENTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE",
    "RECEIPT_SNAPSHOT_SELF_VERIFICATION_ARTIFACTS_EXCLUDED_FROM_CANDIDATE_EVIDENCE",
]:
    assert rule in gov["hard_rules"], rule

env = dict(os.environ)
env["PYTHONPATH"] = str(ROOT)
cp = subprocess.run(
    [sys.executable, "-m", "unittest", "canonical.tests.test_proof_atom_receipt_index_v2", "-v"],
    cwd=ROOT,
    env=env,
    text=True,
    capture_output=True,
)
print(cp.stdout)
print(cp.stderr, file=sys.stderr)
assert cp.returncode == 0, cp.returncode

sys.path.insert(0, str(ROOT))
from canonical.runtime.proof_atom_receipt_index_v2 import build_index

frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
overlay = load("canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json")
with tempfile.TemporaryDirectory() as td:
    out = build_index(frontier, overlay, root=Path(td))
assert out["status"].startswith("PASS"), out
assert out["canonical_atom_count"] == 40, out
assert all(x["atom_id"].startswith("PA1:") for x in out["atoms"]), out
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print(json.dumps({
    "status": "PASS",
    "brain_head": "c95f5e07dbe9e8b18375c0341610184173b3a679",
    "exact_brain_blob_count": len(EXPECTED),
    "canonical_atom_count": out["canonical_atom_count"],
    "pa1_identity_preserved": True,
    "receipt_index_self_reflection_quarantined": True,
    "receipt_snapshot_self_reflection_quarantined": True,
    "declared_corpus_restatement_quarantined": True,
    "credit_delta": 0,
}, indent=2, sort_keys=True))
