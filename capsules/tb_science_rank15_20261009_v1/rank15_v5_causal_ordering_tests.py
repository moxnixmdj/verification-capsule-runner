from __future__ import annotations

import inspect
import unittest

from canonical.runtime import harbor_science_agent_v5 as agent


class Rank15V5CausalOrderingTests(unittest.TestCase):
    def test_intent_commit_precedes_effect(self):
        source = inspect.getsource(agent.run_science_goal)
        intent = '"PLANNER_PROPOSAL_ACTION_INTENT"'
        effect = 'action_receipt = await transport.exec('
        self.assertEqual(source.count(intent), 1)
        self.assertLess(source.index(intent), source.index(effect))

    def test_state_commit_follows_verification(self):
        source = inspect.getsource(agent.run_science_goal)
        verify = 'verify_receipt = await transport.exec('
        state = '"ACTION_VERIFY_STATE_COMMIT"'
        self.assertEqual(source.count(state), 1)
        self.assertLess(source.index(verify), source.index(state))

    def test_controller_requires_journal_session(self):
        source = inspect.getsource(agent.HarborScienceAgent.run)
        self.assertIn("BRAIN_CAUSAL_JOURNAL_DIR_REQUIRED", source)
        self.assertIn("journal_session=journal_session", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
