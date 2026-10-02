import unittest
from scorer import extract_declared_answer,strict_reference_verdict,score_predictions

class Tests(unittest.TestCase):
    def test_exact(self): self.assertTrue(strict_reference_verdict("Answer: A","A").correct)
    def test_strict_lower_bound(self): self.assertFalse(strict_reference_verdict("Answer: 0.5","1/2").correct)
    def test_multiple(self):
        a,r=extract_declared_answer("Answer: A\nAnswer: B");self.assertIsNone(a);self.assertEqual(r,"ANSWER_LINE_COUNT_2")
    def test_missing(self):
        r=score_predictions({},[{"id":"q","answer":"A"}]);self.assertEqual(r["accuracy_percent"],0.0)
    def test_no_equivalence_overclaim(self):
        r=score_predictions({"q":"Answer: A"},[{"id":"q","answer":"A"}]);self.assertFalse(r["official_score_equivalence_claimed"])

if __name__=="__main__": unittest.main()
