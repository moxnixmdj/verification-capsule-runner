import unittest
from semantic_identifiability_gate import adjudicate

def alt(i, meaning, src=True, ctx=True, material=True, discriminator="external fact"):
    return {
        "id": i, "meaning": meaning,
        "consistent_with_source": src,
        "consistent_with_authorized_context": ctx,
        "materially_distinct": material,
        "discriminator": discriminator,
    }

class IndependentSemanticIdentifiability(unittest.TestCase):
    def test_unique_when_all_material_competitors_are_rejected(self):
        r=adjudicate([alt("u","required"),alt("x","optional",src=False)])
        self.assertEqual((r["status"],r["interpretation"]["id"]),("UNIQUE","u"))

    def test_does_not_choose_between_two_supported_meanings(self):
        r=adjudicate([alt("a","first"),alt("b","second")])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual([x["id"] for x in r["ambiguity_witness"]],["a","b"])

    def test_ambiguity_requires_discriminating_evidence(self):
        r=adjudicate([alt("a","first",discriminator=""),alt("b","second",discriminator="authority")])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual(r["missing_discriminators"],["a"])
        self.assertEqual(r["next"],"ACQUIRE_AUTHORIZED_DISCRIMINATING_EVIDENCE")

    def test_unknown_evidence_never_becomes_truth(self):
        for field in ("consistent_with_source","consistent_with_authorized_context","materially_distinct"):
            x=alt("a","meaning"); x[field]=None
            self.assertEqual(adjudicate([x])["status"],"FAIL_CLOSED")

    def test_zero_supported_meanings_fail(self):
        self.assertEqual(adjudicate([alt("a","x",src=False)])["status"],"FAIL_CLOSED")

    def test_duplicate_identity_fails(self):
        r=adjudicate([alt("a","x"),alt("a","y")])
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_paraphrase_marked_nonmaterial_does_not_create_false_ambiguity(self):
        r=adjudicate([alt("a","semantic object"),alt("p","paraphrase",material=False)])
        self.assertEqual(r["status"],"UNIQUE")

if __name__=="__main__":
    unittest.main()
