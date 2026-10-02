from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BRAIN_REF="c95f5e07dbe9e8b18375c0341610184173b3a679"
EXPECTED={
  "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
  "canonical/runtime/proof_atom_receipt_index_v2.py": "5f11b47dc27bfb019bef13cf64a0ef25d7ba1a1f",
  "canonical/tests/test_proof_atom_receipt_index_v2.py": "14103ef7c96330a281367409a5b76a0a74e7129d",
  "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
  "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229",
  "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json": "7168f55492135d1cf5a865c27f564126db8746f7"
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

for rel, expected in EXPECTED.items():
    data=(ROOT/rel).read_bytes()
    got=git_blob_sha(data)
    assert got==expected, (rel,got,expected)

subprocess.run(
    [sys.executable,"-m","unittest","canonical.tests.test_proof_atom_receipt_index_v2","-v"],
    cwd=ROOT,check=True
)

sys.path.insert(0,str(ROOT))
from canonical.runtime.proof_atom_receipt_index_v2 import build_index

frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())

with tempfile.TemporaryDirectory() as td:
    out=build_index(frontier,overlay,root=Path(td))
assert out["status"].startswith("PASS"), out
assert out["canonical_atom_count"]==40, out
assert len(out["canonical_atom_manifest_sha256"])==64, out
assert len(out["scanned_corpus_manifest_sha256"])==64, out
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert all(x["atom_id"].startswith("PA1:") for x in out["atoms"])

print(json.dumps({
  "status":"PASS",
  "brain_ref":BRAIN_REF,
  "canonical_atom_count":out["canonical_atom_count"],
  "canonical_atom_manifest_sha256":out["canonical_atom_manifest_sha256"],
  "empty_corpus_manifest_sha256":out["scanned_corpus_manifest_sha256"],
  "exact_brain_blobs":EXPECTED
},sort_keys=True))
