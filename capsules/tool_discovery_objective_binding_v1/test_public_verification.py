from pathlib import Path
import json, unittest
from canonical.runtime.tool_discovery_t2_t3_objective_binding_validator import validate

ROOT=Path(__file__).resolve().parent

class PublicVerification(unittest.TestCase):
    def test_exact_brain_binding(self):
        out=validate(ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS")
        self.assertTrue(out["diagnostic_all_pass"])
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
