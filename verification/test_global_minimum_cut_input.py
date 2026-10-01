import json
import unittest
from pathlib import Path
from minimum_reality_cut import solve

ROOT=Path(__file__).parent

class GlobalMinimumCutInputTests(unittest.TestCase):
    def test_exact_current_frontier_is_unresolvable_only_for_unbarred_family_proofs(self):
        data=json.loads((ROOT/"global_minimum_cut_input.json").read_text())
        out=solve(data)
        self.assertFalse(out["exact_minimum"])
        self.assertEqual(out["status"],"UNRESOLVABLE_WITH_DECLARED_OBSERVATIONS")
        self.assertEqual(out["missing_distinctions"],sorted(data["expected_missing_distinctions"]))

    def test_graph_fits_exact_solver_limits(self):
        data=json.loads((ROOT/"global_minimum_cut_input.json").read_text())
        self.assertLessEqual(len(data["distinctions"]),24)
        self.assertLessEqual(len(data["observations"]),64)
        self.assertEqual(len(data["distinctions"]),23)

    def test_no_rank23_fresh_execution_observation_is_declared(self):
        data=json.loads((ROOT/"global_minimum_cut_input.json").read_text())
        ids={o["id"] for o in data["observations"]}
        self.assertFalse(any("RANK23" in x for x in ids))

if __name__=="__main__":
    unittest.main()
