from __future__ import annotations
import hashlib, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json": "9f5da1452a15a67ed6fd06ae5b5ff9534e783a5d",
  "canonical/runtime/research_t3_objective_binding_validator.py": "3dbbb1851615265dceadc3a3213c6d37c33d7822",
  "canonical/tests/test_research_t3_objective_binding_validator.py": "c418c49559f30f1037f91f942d25ea2dbbe6c6ee",
  "canonical/governance/OBJECTIVE_ORACLE_DOMINANCE_LIVE_INPUT_V1.json": "c1dad2dcb63be8d9dd50ba5212a5b099966f1f07",
  "canonical/governance/GLOBAL_TERMINAL_SELECTION_KERNEL_V1.json": "669afcde50302e76c1b0a1f6b186aaafa8730515",
  "canonical/runtime/research_control_information_safe_candidate.py": "cd6bf6e4163bbba64878b856766b1af4372d68bc",
  "canonical/runtime/research_control_information_safe_proof.py": "16c47efee0e0e38f479163d1285d7079798efdaf",
  "canonical/tests/test_research_control_information_safe.py": "ab540c8bb91bd9e7fb024f7d94d13253a7fc3d05",
  "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "860cd929e3b7fdab6befec5bf052479dc4ae41ac",
  "canonical/governance/OUTER_TERMINAL_MULTIPLEX_PORTFOLIOS_V1.json": "7c49e3a44dc9a827e84a12b572ea6b8e9b2fa1f5",
  "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "afa00109031d638fef32cc3fe10be18786605c39",
  "canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json": "46834cff249f02cec1046e2f7188e1b5e1b24ab1"
}

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,expected in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(blob(p),expected,rel)

if __name__=="__main__":
    unittest.main(verbosity=2)
