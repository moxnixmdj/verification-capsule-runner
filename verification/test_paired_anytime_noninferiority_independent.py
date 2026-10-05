import itertools
import math
import unittest

import paired_anytime_noninferiority as candidate

REQUIRED_TRUE = (
    "population_frozen_before_results",
    "selection_rule_frozen_before_results",
    "case_order_frozen_before_results",
    "scorer_frozen_before_results",
    "brain_candidate_frozen_before_results",
    "opus_model_configuration_frozen_before_results",
    "checkpoint_schedule_frozen_before_results",
    "independent_acceptance",
    "case_pairs_independent_conditionally_on_frozen_population",
    "same_case_pairing",
    "zero_case_replacement",
    "zero_adaptive_case_selection",
    "zero_tuning_replay",
    "zero_incremental_spend",
)


def payload(brain, opus, schedule, alpha=0.05):
    d = {
        "proof_mode": candidate.PROOF_MODE,
        "brain_case_scores": list(brain),
        "opus_case_scores": list(opus),
        "alpha": alpha,
        "checkpoint_schedule": list(schedule),
    }
    d.update({key: True for key in REQUIRED_TRUE})
    return d


class IndependentPairedAnytimeVerifier(unittest.TestCase):
    def test_exact_formula_recomputed_independently(self):
        brain = [1.0, 0.8, 1.0, 0.7, 0.9, 1.0, 0.8, 1.0]
        opus = [0.0, 0.2, 0.1, 0.2, 0.1, 0.0, 0.1, 0.0]
        out = candidate.evaluate(payload(brain, opus, [8, 16, 32]))
        k = 1
        alpha_k = 0.05 * 6.0 / (math.pi**2 * k*k)
        mean = sum(b-o for b,o in zip(brain, opus)) / 8.0
        eps = math.sqrt(2.0 * math.log(1.0/alpha_k) / 8.0)
        self.assertAlmostEqual(out["checkpoint_alpha"], alpha_k, places=15)
        self.assertAlmostEqual(out["paired_mean_advantage"], mean, places=15)
        self.assertAlmostEqual(out["hoeffding_epsilon"], eps, places=15)
        self.assertAlmostEqual(out["paired_advantage_one_sided_lower_bound"], mean-eps, places=15)

    def test_infinite_alpha_spending_budget_is_bounded(self):
        alpha = 0.05
        partial = sum(alpha * 6.0/(math.pi**2*k*k) for k in range(1, 200000))
        self.assertLess(partial, alpha)
        self.assertLess(alpha-partial, 1e-6)

    def test_every_attestation_gate_fails_closed(self):
        base = payload([1.0]*8, [0.0]*8, [8,16])
        for key in REQUIRED_TRUE:
            mutated = dict(base)
            mutated[key] = False
            out = candidate.evaluate(mutated)
            self.assertFalse(out["pass"], key)
            self.assertEqual(out["status"], "FAIL_CLOSED", key)
            self.assertIn(key.upper()+"_NOT_TRUE", out["errors"], key)

    def test_invalid_checkpoint_mutations_fail_closed(self):
        variants = ([8,8], [16,8], [0,8], [8.0,16], [], [4,16])
        for schedule in variants:
            out = candidate.evaluate(payload([1.0]*8,[0.0]*8,schedule))
            if schedule == [4,16]:
                self.assertIn("CURRENT_SAMPLE_COUNT_NOT_PREDECLARED_CHECKPOINT", out["errors"])
            else:
                self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_null_optional_stopping_rate_for_symmetric_extreme_pairs_is_below_alpha(self):
        # Enumerate all 2^8 independent Rademacher paired differences under mean zero.
        # Checkpoints are 4 and 8. At each prefix, encode +1 as (Brain=1,Opus=0)
        # and -1 as (Brain=0,Opus=1), and stop if the candidate would pass.
        alpha = 0.05
        pass_count = 0
        total = 0
        for signs in itertools.product((-1,1), repeat=8):
            total += 1
            passed = False
            for n in (4,8):
                brain = [1.0 if s == 1 else 0.0 for s in signs[:n]]
                opus = [0.0 if s == 1 else 1.0 for s in signs[:n]]
                out = candidate.evaluate(payload(brain, opus, [4,8], alpha=alpha))
                if out["pass"]:
                    passed = True
                    break
            pass_count += int(passed)
        empirical_exact = pass_count / total
        self.assertLessEqual(empirical_exact, alpha)

    def test_nonregistered_optional_peek_is_rejected(self):
        out = candidate.evaluate(payload([1.0]*6,[0.0]*6,[4,8,16]))
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_SAMPLE_COUNT_NOT_PREDECLARED_CHECKPOINT", out["errors"])

    def test_later_checkpoint_uses_its_own_smaller_alpha_slice(self):
        first = candidate.evaluate(payload([1.0]*8,[0.0]*8,[8,16]))
        second = candidate.evaluate(payload([1.0]*16,[0.0]*16,[8,16]))
        self.assertEqual(first["checkpoint_index"], 1)
        self.assertEqual(second["checkpoint_index"], 2)
        self.assertAlmostEqual(second["checkpoint_alpha"], first["checkpoint_alpha"]/4.0, places=15)

    def test_no_credit_fields_move_on_pass(self):
        out = candidate.evaluate(payload([1.0]*8,[0.0]*8,[8]))
        self.assertTrue(out["pass"])
        for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            self.assertEqual(out[key], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
