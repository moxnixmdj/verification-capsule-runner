from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/proof_atom_receipt_index_v2.py": "7702edd75028e51d96f27ed64a4b388c5e370448",
  "canonical/tests/test_proof_atom_receipt_index_v2.py": "5c5d5cdf7a41cfc4644416d5291a7000202699a7",
  "canonical/runtime/proof_atom_receipt_snapshot_v1.py": "38dac15668373498495ec5abdbfe64d6072d7605",
  "canonical/tests/test_proof_atom_receipt_snapshot_v1.py": "e5cef057804c773380762e821b4f540f8f6d0f7a",
  "canonical/runtime/canonical_proof_atom_basis_v2.py": "5b5957f353edab6c86a34f947ef253099822b0d1",
  "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json": "4b5517dbd12978f8ffe481fb775e85592c7790c8",
  "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json": "898e450c62c06cf6d1a4a3f826a255da9161a229"
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

for rel,expected in EXPECTED.items():
    got=git_blob_sha((ROOT/rel).read_bytes())
    assert got==expected,(rel,got,expected)

cp=subprocess.run(
    [sys.executable,"-m","unittest",
     "canonical.tests.test_proof_atom_receipt_index_v2",
     "canonical.tests.test_proof_atom_receipt_snapshot_v1","-v"],
    cwd=ROOT,text=True,capture_output=True
)
print(cp.stdout)
print(cp.stderr,file=sys.stderr)
assert cp.returncode==0,cp.returncode

sys.path.insert(0,str(ROOT))
from canonical.runtime.proof_atom_receipt_index_v2 import build_index
frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text())
import tempfile
with tempfile.TemporaryDirectory() as td:
    out=build_index(frontier,overlay,root=Path(td))
assert out["status"].startswith("PASS"),out
assert out["canonical_atom_count"]==40,out
assert out["declared_candidate_file_count"]==0,out
assert out["scanned_file_count"]==0,out
assert out["unsearched_candidate_file_count"]==0,out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out
print(json.dumps({"status":"PASS","exact_brain_blobs":EXPECTED,"canonical_atom_count":40,
                  "verified_invariants":["OVERSIZE_FAIL_CLOSED","NON_UTF8_FAIL_CLOSED",
                  "TRACKED_UNIVERSE_EXHAUSTIVE","SKIP_WORKTREE_OMISSION_FAIL_CLOSED",
                  "ZERO_CREDIT"]},sort_keys=True))
