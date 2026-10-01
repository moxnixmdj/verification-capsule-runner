import json, unittest
from pathlib import Path
from minimum_reality_cut import solve
ROOT=Path(__file__).parent
class CutV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cut=json.loads((ROOT/"cut.json").read_text())
        cls.proto=json.loads((ROOT/"protocols.json").read_text())
        cls.matched=json.loads((ROOT/"matched.json").read_text())
    def test_exact_minimum(self):
        out=solve(self.cut)
        self.assertTrue(out["exact_minimum"])
        self.assertEqual(out["status"],"EXACT_MINIMUM")
        self.assertEqual(out["observation_count"],11)
        self.assertEqual(out["total_cost"],13.0)
        self.assertEqual(set(out["selected_observations"]),{o["id"] for o in self.cut["observations"]})
        self.assertEqual(set(out["unresolved_distinctions"]),set(self.cut["distinctions"]))
    def test_three_bundle_cover_sets_exact(self):
        p={b["id"]:set(b["covers"]) for b in self.proto["bundles"]}
        c={o["id"]:set(o["covers"]) for o in self.cut["observations"] if o["id"] in p}
        self.assertEqual(c,p)
        self.assertEqual(len(p),3)
    def test_ten_formerly_missing_family_proofs_covered_exactly_once(self):
        missing=set(self.proto["previously_missing_family_proofs"])
        counts={x:0 for x in missing}
        for b in self.proto["bundles"]:
            for x in b["covers"]:
                if x in counts: counts[x]+=1
        self.assertTrue(all(v==1 for v in counts.values()),counts)
    def test_protocols_zero_credit_and_exact_comparator(self):
        self.assertEqual(self.proto["capability_credit_delta"],0)
        self.assertEqual(self.proto["family_credit_delta"],0)
        self.assertEqual(self.matched["target"]["exact_comparator"],"Claude Opus 5.5")
        self.assertFalse(self.matched["target"]["proxy_comparator_allowed"])
    def test_rank23_not_admitted(self):
        self.assertFalse(any("RANK23" in o["id"] for o in self.cut["observations"]))
if __name__=="__main__": unittest.main()
