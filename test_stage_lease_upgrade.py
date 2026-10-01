import unittest

from session_bridge.acceptance_contract import validate_lease_upgrade


def lease(scope, *, rank=17, task="data-anonymization", session="data-anonymization-20261001-v1", execute=False):
    return {
        "schema": "BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1",
        "session_id": session,
        "task": task,
        "authorization": True,
        "lease_merged_to_main": True,
        "canonical_brain_commit": "a" * 40,
        "canonical_lease_path": "canonical/governance/LEASE_TEST.json",
        "sample_rank": rank,
        "scope": scope,
        "task_execution_authorized": execute,
        "replay_for_credit": False,
    }


class LeaseUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.stage_b = lease("STAGE_B_INSTRUCTION_EXPOSURE_ONLY", execute=False)
        self.stage_c = lease("STAGE_C_ONE_SHOT_EXECUTION", execute=True)

    def check(self, current=None, candidate=None, *, next_burst=0, acceptance_hash=None):
        return validate_lease_upgrade(
            current or self.stage_b,
            candidate or self.stage_c,
            "data-anonymization-20261001-v1",
            "data-anonymization",
            next_burst=next_burst,
            acceptance_hash=acceptance_hash,
        )

    def test_exact_monotonic_upgrade_passes(self):
        self.assertEqual(self.check(), [])

    def test_rank_swap_fails(self):
        x=lease("STAGE_C_ONE_SHOT_EXECUTION", rank=18, execute=True)
        self.assertIn("LEASE_UPGRADE_RANK_MISMATCH", self.check(candidate=x))

    def test_wrong_target_scope_fails(self):
        x=lease("STAGE_B_INSTRUCTION_EXPOSURE_ONLY", execute=False)
        self.assertIn("LEASE_UPGRADE_TARGET_SCOPE_INVALID", self.check(candidate=x))

    def test_post_burst_upgrade_fails(self):
        self.assertIn("LEASE_UPGRADE_AFTER_BUILDER_STARTED", self.check(next_burst=1))

    def test_post_acceptance_freeze_upgrade_fails(self):
        self.assertIn("LEASE_UPGRADE_AFTER_ACCEPTANCE_FROZEN", self.check(acceptance_hash="frozen"))

    def test_task_swap_fails_authorization(self):
        x=lease("STAGE_C_ONE_SHOT_EXECUTION", task="other-task", execute=True)
        self.assertIn("LEASE_TASK_MISMATCH", self.check(candidate=x))

    def test_replay_enabled_fails(self):
        x=dict(self.stage_c); x["replay_for_credit"]=True
        self.assertIn("LEASE_UPGRADE_REPLAY_POLICY_INVALID", self.check(candidate=x))


if __name__ == "__main__":
    unittest.main()
