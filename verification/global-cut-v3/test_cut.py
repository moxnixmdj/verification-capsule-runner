import json, unittest
from pathlib import Path
from minimum_reality_cut import solve
ROOT=Path(__file__).parent
class CutV3(unittest.TestCase):
    def test_exact_brain_mirror_hash(self):
        import hashlib
        raw=(ROOT/"cut.json").read_bytes()
        git_blob=b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw
        self.assertEqual(hashlib.sha1(git_blob).hexdigest(),"c0ceaba4919201119faa94d92abc6b8efacc86d0")

    def test_exact_compressed_cut(self):
        data=json.loads((ROOT/"cut.json").read_text())
        out=solve(data)
        self.assertTrue(out["exact_minimum"])
        self.assertEqual(out["status"],"EXACT_MINIMUM")
        self.assertEqual(out["observation_count"],15)
        self.assertEqual(out["total_cost"],16.0)
        self.assertEqual(set(out["unresolved_distinctions"]),set(data["distinctions"]))
        self.assertEqual(set(out["selected_observations"]),{o["id"] for o in data["observations"]})
    def test_zero_cost_members_present_and_rank23_absent(self):
        data=json.loads((ROOT/"cut.json").read_text())
        z={o["id"] for o in data["observations"] if o["cost"]==0}
        self.assertEqual(z,set(data["expected_exact_minimum"]["zero_new_information_members"]))
        self.assertFalse(any("RANK23" in o["id"] for o in data["observations"]))
if __name__=="__main__": unittest.main()
