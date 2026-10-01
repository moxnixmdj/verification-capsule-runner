import unittest
from session_bridge.acceptance_contract import (
    validate_execution_budget,
    validate_lease_authorization,
)

def stage_c_lease(**overrides):
    x = {
        "schema": "BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1",
        "session_id": "s",
        "task": "t",
        "authorization": True,
        "lease_merged_to_main": True,
        "canonical_brain_commit": "a" * 40,
        "canonical_lease_path": "canonical/governance/LEASE.json",
        "sample_rank": 19,
        "scope": "STAGE_C_ONE_SHOT_EXECUTION",
        "task_execution_authorized": True,
        "execution_count_allowed": 1,
        "terminal_verifier_count_allowed": 1,
        "replay_for_credit": False,
    }
    x.update(overrides)
    return x

class TestCanonicalStageCBudgets(unittest.TestCase):
    def test_rank18_regression_second_burst_is_rejected(self):
        lease = stage_c_lease(execution_count_allowed=1)
        self.assertEqual(
            validate_execution_budget(
                lease, accepted_bursts=0, terminal_verifier_count=0, action="BURST"
            ),
            [],
        )
        self.assertIn(
            "CANONICAL_EXECUTION_BUDGET_EXHAUSTED",
            validate_execution_budget(
                lease, accepted_bursts=1, terminal_verifier_count=0, action="BURST"
            ),
        )

    def test_zero_execution_budget_rejects_first_burst(self):
        self.assertIn(
            "CANONICAL_EXECUTION_BUDGET_EXHAUSTED",
            validate_execution_budget(
                stage_c_lease(execution_count_allowed=0),
                accepted_bursts=0,
                terminal_verifier_count=0,
                action="BURST",
            ),
        )

    def test_terminal_budget_is_independent_and_single_use(self):
        lease = stage_c_lease(terminal_verifier_count_allowed=1)
        self.assertEqual(
            validate_execution_budget(
                lease, accepted_bursts=1, terminal_verifier_count=0, action="TERMINAL"
            ),
            [],
        )
        self.assertIn(
            "CANONICAL_TERMINAL_BUDGET_EXHAUSTED",
            validate_execution_budget(
                lease, accepted_bursts=1, terminal_verifier_count=1, action="TERMINAL"
            ),
        )

    def test_stage_b_or_revoked_lease_cannot_execute(self):
        lease = stage_c_lease(task_execution_authorized=False)
        self.assertIn(
            "TASK_EXECUTION_NOT_AUTHORIZED",
            validate_execution_budget(
                lease, accepted_bursts=0, terminal_verifier_count=0, action="BURST"
            ),
        )

    def test_stage_c_authorization_requires_explicit_budgets(self):
        bad = stage_c_lease()
        del bad["execution_count_allowed"]
        del bad["terminal_verifier_count_allowed"]
        errors = validate_lease_authorization(bad, "s", "t")
        self.assertIn("CANONICAL_EXECUTION_BUDGET_INVALID", errors)
        self.assertIn("CANONICAL_TERMINAL_BUDGET_INVALID", errors)

    def test_boolean_is_not_accepted_as_integer_budget(self):
        errors = validate_lease_authorization(
            stage_c_lease(execution_count_allowed=True), "s", "t"
        )
        self.assertIn("CANONICAL_EXECUTION_BUDGET_INVALID", errors)

if __name__ == "__main__":
    unittest.main(verbosity=2)
