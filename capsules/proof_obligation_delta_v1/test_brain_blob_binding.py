from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
EXPECTED={
    "canonical/runtime/proof_obligation_delta_compiler_v1.py":"dea41dc780c92efdd7c8b4b8551129197ab8cca8",
    "canonical/tests/test_proof_obligation_delta_compiler_v1.py":"75eebd1ac6f50073bfef6dbe63433ec4ae7df096",
    "canonical/governance/PROOF_OBLIGATION_DELTA_COMPILER_ACTIVATION_V1.json":"c752dc3ba705362986739dca99857075531dd784",
}
CAPSULE=ROOT/"canonical"

def git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

class BrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        mapping={
            "canonical/runtime/proof_obligation_delta_compiler_v1.py":CAPSULE/"runtime/proof_obligation_delta_compiler_v1.py",
            "canonical/tests/test_proof_obligation_delta_compiler_v1.py":CAPSULE/"tests/test_proof_obligation_delta_compiler_v1.py",
            "canonical/governance/PROOF_OBLIGATION_DELTA_COMPILER_ACTIVATION_V1.json":CAPSULE/"governance/PROOF_OBLIGATION_DELTA_COMPILER_ACTIVATION_V1.json",
        }
        for key,path in mapping.items():
            self.assertEqual(git_blob_sha(path),EXPECTED[key],key)

if __name__=="__main__":
    unittest.main(verbosity=2)
