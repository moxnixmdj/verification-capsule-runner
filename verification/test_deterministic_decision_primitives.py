import math, random, unittest
from deterministic_decision_primitives import (
    hard_constraint_admissibility, expected_utility, rank_actions_by_expected_utility,
    bayes_posterior, entropy_bits, expected_information_gain, intervenability_from_authority
)

class TestDecisionPrimitives(unittest.TestCase):
    def test_hard_constraints(self):
        c={"scope":"A","available":True,"kind":"tool"}
        self.assertTrue(hard_constraint_admissibility(c,required_equal={"scope":"A"},required_present=["kind"]).admissible)
        d=hard_constraint_admissibility(c,required_equal={"scope":"B"},forbidden_equal={"available":True})
        self.assertFalse(d.admissible)
        self.assertIn("REQUIRED_EQUAL:scope",d.reasons)
        self.assertIn("FORBIDDEN_EQUAL:available",d.reasons)

    def test_expected_utility_and_rank(self):
        self.assertAlmostEqual(expected_utility([(0.25,4),(0.75,0)]),1.0)
        ranked=rank_actions_by_expected_utility({"a":[(1,2)],"b":[(0.5,10),(0.5,-2)]},fixed_costs={"b":1})
        self.assertEqual(ranked[0][0],"b")
        self.assertAlmostEqual(ranked[0][1],3.0)
        with self.assertRaises(ValueError): expected_utility([(0.4,1),(0.4,2)])

    def test_bayes_known_case(self):
        post=bayes_posterior({"fair":0.5,"biased":0.5},{"fair":0.5,"biased":0.9})
        self.assertAlmostEqual(post["biased"],0.9/(0.5+0.9))
        self.assertAlmostEqual(sum(post.values()),1.0)

    def test_bayes_random_normalizes_and_matches_ratio(self):
        rng=random.Random(20261001)
        for _ in range(1000):
            a=rng.random(); prior={"a":a,"b":1-a}
            la=max(rng.random(),1e-9); lb=max(rng.random(),1e-9)
            post=bayes_posterior(prior,{"a":la,"b":lb})
            self.assertAlmostEqual(sum(post.values()),1.0,places=12)
            if prior["a"]>0 and prior["b"]>0:
                self.assertAlmostEqual(post["a"]/post["b"],(prior["a"]*la)/(prior["b"]*lb),places=10)

    def test_information_gain(self):
        prior={0:0.5,1:0.5}
        independent={0:{"x":0.3,"y":0.7},1:{"x":0.3,"y":0.7}}
        self.assertAlmostEqual(expected_information_gain(prior,independent),0.0,places=12)
        perfect={0:{"x":1.0,"y":0.0},1:{"x":0.0,"y":1.0}}
        self.assertAlmostEqual(expected_information_gain(prior,perfect),1.0,places=12)
        noisy={0:{"x":0.8,"y":0.2},1:{"x":0.2,"y":0.8}}
        g=expected_information_gain(prior,noisy)
        self.assertGreater(g,0.0); self.assertLess(g,1.0)

    def test_intervenability_is_authority_not_telemetry(self):
        catalog={
          "restart_service":[{"enabled":True,"policy_allowed":True}],
          "kernel_param":[{"enabled":True,"policy_allowed":False}],
          "disabled":[{"enabled":False,"policy_allowed":True}],
          "unclear":[{"enabled":True}],
          "empty":[]
        }
        self.assertEqual(intervenability_from_authority("restart_service",catalog),"INTERVENABLE")
        self.assertEqual(intervenability_from_authority("kernel_param",catalog),"NOT_INTERVENABLE")
        self.assertEqual(intervenability_from_authority("disabled",catalog),"NOT_INTERVENABLE")
        self.assertEqual(intervenability_from_authority("unclear",catalog),"UNKNOWN")
        self.assertEqual(intervenability_from_authority("empty",catalog),"NOT_INTERVENABLE")
        self.assertEqual(intervenability_from_authority("missing",catalog),"UNKNOWN")

if __name__=="__main__":
    unittest.main(verbosity=2)
