from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "capsules/proof_optimizer_primitives/canonical/runtime/proof_coverage_compiler.py": "f9b7eb23ec749d542392f36d89ddf69d9f8d3c87",
  "capsules/proof_optimizer_primitives/canonical/runtime/build_current_proof_coverage_manifest.py": "2a040c01afdb5d80d8409ffe9542339e3df36ceb",
  "capsules/proof_optimizer_primitives/canonical/tests/test_proof_coverage_compiler.py": "0dd8538ecc1620b354eb4387090c997ba18aeffb",
  "capsules/proof_optimizer_primitives/canonical/tests/test_build_current_proof_coverage_manifest.py": "9816b3a67f48c6aca48a8ed1f331bc820420d5b1",
  "capsules/proof_optimizer_primitives/canonical/runtime/proof_dependency_guard.py": "a21eb144b7a9d3282d33b8aaad816749ee0e2fa0",
  "capsules/proof_optimizer_primitives/canonical/tests/test_proof_dependency_guard.py": "30691a15affd3d00a49ebd32ddc13064de0af1ac"
}

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

class BrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel, expected in EXPECTED.items():
            local=ROOT / rel.replace("capsules/proof_optimizer_primitives/","",1)
            self.assertTrue(local.is_file(), rel)
            self.assertEqual(git_blob_sha(local), expected, rel)

if __name__=="__main__":
    unittest.main(verbosity=2)
