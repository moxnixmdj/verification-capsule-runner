from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
m = json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for src, expected in m["exact_brain_blobs"].items():
    actual = git_blob_sha(ROOT/src)
    assert actual == expected, (src, actual, expected)

sys.path.insert(0, str(ROOT))
subprocess.run([sys.executable, "-m", "py_compile",
    str(ROOT/"canonical/runtime/canonical_proof_atom_basis_v2.py"),
    str(ROOT/"canonical/runtime/proof_atom_receipt_index_v2.py"),
    str(ROOT/"canonical/runtime/proof_atom_receipt_snapshot_v1.py")], check=True)
subprocess.run([sys.executable, "-m", "unittest",
    "canonical.tests.test_proof_atom_receipt_snapshot_v1", "-v"], cwd=ROOT, check=True)

print(json.dumps({
  "status":"PASS",
  "exact_brain_blob_count":len(m["exact_brain_blobs"]),
  "snapshot_runner_unit_tests":"PASS",
  "clean_git_fixture_sealing":"PASS",
  "tracked_drift_fail_closed":"PASS",
  "untracked_candidate_fail_closed":"PASS",
  "credit_delta":0
}, indent=2, sort_keys=True))
