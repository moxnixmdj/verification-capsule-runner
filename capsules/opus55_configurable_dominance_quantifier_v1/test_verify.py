import unittest
import verify

class ConfigurableDominanceQuantifierV1Tests(unittest.TestCase):
    def test_exact_source_blob_and_zero_credit(self):
        src = verify.load_source()
        self.assertTrue(src["quantifier_correction"]["fixed_policy_theorem_remains_true"])
        self.assertEqual(src["accounting"]["acceptance_credit_delta"], 0)
        self.assertFalse(src["fresh_reality_authority"])

    def test_quantifier_order_constructive_separation(self):
        rewards = [(1,0,0), (0,1,0), (0,0,1)]
        self.assertTrue(verify.no_single_deterministic_action_maximizes_all(rewards))
        self.assertEqual([verify.task_conditioned_argmax(r) for r in rewards], [0,1,2])

    def test_argmax_dominates_arbitrary_target_distributions_on_bound_stratum(self):
        reward = (0.2, 0.9, 0.4)
        dists = [
            (1,0,0),
            (0,1,0),
            (0,0,1),
            (1/3,1/3,1/3),
            (0.8,0.1,0.1),
            (0.05,0.9,0.05),
        ]
        out = verify.convex_dominance_witness(reward, dists)
        self.assertAlmostEqual(out["brain_value"], 0.9)
        self.assertTrue(all(v <= 0.9 + 1e-12 for v in out["target_values"]))

    def test_hidden_evaluator_fails_closed(self):
        out = verify.certify_explicit_exact_task(
            (0,1),
            evaluator_admissibly_available=False,
            exact_optimization_terminating=True,
            resource_valid=True,
            optimizer_brain_owned=True,
        )
        self.assertFalse(out["dominance_authorized"])

    def test_nonterminating_or_resource_invalid_optimizer_fails_closed(self):
        for exact, resource in [(False,True),(True,False)]:
            out = verify.certify_explicit_exact_task(
                (0,1),
                evaluator_admissibly_available=True,
                exact_optimization_terminating=exact,
                resource_valid=resource,
                optimizer_brain_owned=True,
            )
            self.assertFalse(out["dominance_authorized"])

    def test_nonowned_optimizer_fails_closed(self):
        out = verify.certify_explicit_exact_task(
            (0,1),
            evaluator_admissibly_available=True,
            exact_optimization_terminating=True,
            resource_valid=True,
            optimizer_brain_owned=False,
        )
        self.assertFalse(out["dominance_authorized"])

    def test_full_independent_recomputation(self):
        out = verify.independently_verify()
        self.assertIn("INDEPENDENT_RECOMPUTATION_PASS", out["status"])
        self.assertEqual(out["source_git_blob_sha"], verify.EXPECTED_BLOB)
        self.assertEqual(out["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(out["accounting"]["ownership_credit_delta"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
