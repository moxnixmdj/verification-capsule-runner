import unittest
from exact_callout_association import solve

class VerifyExactAssociation(unittest.TestCase):
    def test_unique(self):
        r=solve([{"id":"A","candidate_targets":["X"]},{"id":"B","candidate_targets":["Y"]}])
        self.assertEqual(r["status"],"UNIQUE")

    def test_ambiguous_returns_witness(self):
        r=solve([{"id":"A","candidate_targets":["X","Y"]}])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertTrue(r["ambiguity_witness"])

    def test_global_distinctness_can_resolve(self):
        r=solve([
            {"id":"A","candidate_targets":["X"]},
            {"id":"B","candidate_targets":["X","Y"]}
        ],distinct_targets=True)
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"]["B"],"Y")

    def test_same_and_different_relations(self):
        r=solve([
            {"id":"A","candidate_targets":["X"]},
            {"id":"B","candidate_targets":["X","Y"]},
            {"id":"C","candidate_targets":["Y"]}
        ],same_target=[["A","B"]],different_target=[["B","C"]])
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"],{"A":"X","B":"X","C":"Y"})

    def test_inconsistent_fails_closed(self):
        r=solve([
            {"id":"A","candidate_targets":["X"]},
            {"id":"B","candidate_targets":["X"]}
        ],distinct_targets=True)
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_unknown_relation_id_fails_closed(self):
        r=solve([{"id":"A","candidate_targets":["X"]}],same_target=[["A","Q"]])
        self.assertEqual(r["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
