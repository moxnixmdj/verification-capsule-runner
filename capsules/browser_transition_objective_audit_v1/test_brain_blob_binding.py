from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/browser_transition_objective_audit_v1.py": "e37548030083627d711f12b85f7c3785aed41081",
    "canonical/tests/test_browser_transition_objective_audit_v1.py": "358fc8cc1d5ea493fe4ab4dd938b697499c29306",
}

def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel, expected in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(), rel)
            self.assertEqual(blob(p), expected, rel)

if __name__ == "__main__":
    unittest.main(verbosity=2)
