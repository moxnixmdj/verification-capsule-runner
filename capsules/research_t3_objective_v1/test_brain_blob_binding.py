from __future__ import annotations
import hashlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json": "a9b1703ec3e1f76db1e1449c32ae1fd0cf9169e3",
  "canonical/runtime/research_t3_objective_binding_validator.py": "4677ffa035ed6819f614c047785d1ce1a811d34a",
  "canonical/tests/test_research_t3_objective_binding_validator.py": "106d5183e61eb5a72513d607cc6f5e5f09e361db",
  "canonical/runtime/research_control_information_safe_candidate.py": "cd6bf6e4163bbba64878b856766b1af4372d68bc",
  "canonical/runtime/research_control_information_safe_proof.py": "16c47efee0e0e38f479163d1285d7079798efdaf",
  "canonical/tests/test_research_control_information_safe.py": "ab540c8bb91bd9e7fb024f7d94d13253a7fc3d05",
  "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "860cd929e3b7fdab6befec5bf052479dc4ae41ac",
  "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "afa00109031d638fef32cc3fe10be18786605c39"
}
def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
class Tests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,expected in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(blob(p),expected,rel)
if __name__=="__main__":unittest.main(verbosity=2)
