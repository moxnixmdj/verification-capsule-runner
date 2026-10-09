from __future__ import annotations

import inspect
import unittest

from canonical.runtime import harbor_science_agent_v5 as agent
import rank15_v5_status_journal_runner as runner


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

    def test_agent_requires_journal_after_start_barrier(self):
        source = inspect.getsource(agent.HarborScienceAgent.run)
        barrier = "await start_barrier.await_start_commit(logical_attempt_id)"
        journal = 'journal_dir = os.environ.get("BRAIN_CAUSAL_JOURNAL_DIR")'
        controller = "result = await run_science_goal("
        self.assertLess(source.index(barrier), source.index(journal))
        self.assertLess(source.index(journal), source.index(controller))

    def test_parent_pumps_journal_and_uses_v5_agent(self):
        run_source = inspect.getsource(runner.run_once)
        command_source = inspect.getsource(runner._harbor_command)
        self.assertIn("process_journal(journal_store)", run_source)
        self.assertIn("qualify_status()", run_source)
        self.assertIn(
            "canonical.runtime.harbor_science_agent_v5:HarborScienceAgent",
            command_source,
        )
        self.assertIn('"-r"', command_source)
        self.assertIn('"0"', command_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
