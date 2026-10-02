from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/objective_oracle_dominance_compiler.py": "c00d59dd0ab7df6ffb0ba5c26a1cb2a5cd82203c",
    "canonical/tests/test_objective_oracle_dominance_compiler.py": "b4df7e088cd4da2889b0e3dc8b03ba9608e04b48",
    "canonical/governance/OBJECTIVE_ORACLE_DOMINANCE_LIVE_INPUT_V1.json": "79d1c88b854f05b73d37734cbb2b4bf5000a5472",
}

def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel, expected in EXPECTED.items():
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(blob(path), expected, rel)

if __name__ == "__main__":
    unittest.main(verbosity=2)
