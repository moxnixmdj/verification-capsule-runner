from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json": "ad790afa864bd8f770c3d8a6e3ac901ed2843d26",
  "canonical/runtime/p3_synthesis_t1_t3_multiplex_preflight.py": "37e67adc87c000f578618eda5c754a7843d4845b",
  "canonical/tests/test_p3_synthesis_t1_t3_multiplex_preflight.py": "43d1ddf66bf5203437d307910f3a7ffaf4bfa14d",
  "canonical/runtime/p3_information_safe_candidate_v3.py": "54bfc7e5ee205aa328863a5ea1ca6f47f864d85a",
  "canonical/runtime/p3_information_safe_proof_suite_v3.py": "7b4fef2a2ba2c84b3499ded1ed4bbaac6714fa42",
  "canonical/verification/P3_INFORMATION_SAFE_V3_PREFLIGHT_VERIFICATION_20261002_V1.json": "c0812ad6e7ee1e1c93d7419ed72f4fc7c9980381",
  "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json": "8b439403a05b4a912f06a8866db25f6e53b52473",
  "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json": "46cce2be4e277485b7c83233630d0e2fe57d06d1",
  "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json": "8c7ffe3d9ff789eddd286496f6de3ce84472c909",
  "canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json": "d8cf10dfbe041f63a43ccf43bd5dcdc8fe6f9e2b"
}

def blob(path: Path)->str:
    d=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode("ascii")+b"\0"+d).hexdigest()

class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,expected in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(blob(p),expected,rel)

if __name__=="__main__":
    unittest.main(verbosity=2)
