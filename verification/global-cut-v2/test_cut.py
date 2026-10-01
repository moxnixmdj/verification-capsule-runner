import json
import unittest
from pathlib import Path
from minimum_reality_cut import solve

ROOT=Path(__file__).parent

class GlobalCutV2(unittest.TestCase):
    def test_all_protocol_holes_closed_and_exact_baseline_exists(self):
        data=json.loads((ROOT/"cut.json").read_text())
        out=solve(data)
        self.assertTrue(out["exact_minimum"])
        self.assertEqual(out["status"],"EXACT_MINIMUM")
        self.assertEqual(out["observation_count"],23)
        self.assertEqual(out["total_cost"],23.0)
        self.assertEqual(set(out["unresolved_distinctions"]),set(data["distinctions"]))
    def test_no_rank23_observation(self):
        data=json.loads((ROOT/"cut.json").read_text())
        self.assertFalse(any("RANK23" in x["id"] for x in data["observations"]))
if __name__=="__main__":
    unittest.main()
