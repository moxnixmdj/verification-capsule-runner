from __future__ import annotations

import inspect
import unittest

from canonical.runtime import harbor_science_agent_v5 as agent
import rank15_v5_status_journal_runner as runner
from execution_guard import terminal_causal_journal_v1 as journal
from execution_guard import github_status_object_store_v1 as status_store


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
        journal_marker = 'journal_dir = os.environ.get("BRAIN_CAUSAL_JOURNAL_DIR")'
        controller = "result = await run_science_goal("
        self.assertLess(source.index(barrier), source.index(journal_marker))
        self.assertLess(source.index(journal_marker), source.index(controller))

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

    def test_max_rank15_intent_and_state_events_fit_status_object_store(self):
        logical = "a" * 64
        requirement_ids = [f"R{i:07d}" for i in range(agent.MAX_REQUIREMENTS)]
        dependency_ids = [
            ("A" + str(i).zfill(2) + "X" * 29)[: agent.science_planner.MAX_ACTION_ID_CHARS]
            for i in range(agent.MAX_CANDIDATES)
        ]
        action_id = "Z" * agent.science_planner.MAX_ACTION_ID_CHARS

        intent_payload = {
            "cycle": agent.MAX_CYCLES - 1,
            "planner_payload_sha256": "1" * 64,
            "planner_request_identity_sha256": "2" * 64,
            "proposal_sha256": "3" * 64,
            "action_id": action_id,
            "command_sha256": "4" * 64,
            "verify_command_sha256": "5" * 64,
            "covers": requirement_ids,
            "depends_on": dependency_ids,
            "action_timeout_sec": agent.MAX_ACTION_TIMEOUT_S,
            "verify_timeout_sec": agent.MAX_VERIFY_TIMEOUT_S,
        }
        intent = journal.make_event(
            logical_attempt_id=logical,
            sequence=0,
            predecessor_sha256=None,
            kind="PLANNER_PROPOSAL_ACTION_INTENT",
            payload=intent_payload,
        )

        state_payload = {
            "cycle": agent.MAX_CYCLES - 1,
            "action_id": action_id,
            "action_returncode": -2147483648,
            "action_stdout_sha256": "6" * 64,
            "action_stderr_sha256": "7" * 64,
            "verification_performed": True,
            "verification_returncode": 2147483647,
            "verification_stdout_sha256": "8" * 64,
            "verification_stderr_sha256": "9" * 64,
            "verified_covers": requirement_ids,
            "resolved_requirement_ids": requirement_ids,
            "coverage_promoted": True,
        }
        state = journal.make_event(
            logical_attempt_id=logical,
            sequence=1,
            predecessor_sha256=intent["event_sha256"],
            kind="ACTION_VERIFY_STATE_COMMIT",
            payload=state_payload,
        )

        intent_bytes = len(journal._canon(intent))
        state_bytes = len(journal._canon(state))
        self.assertLess(intent_bytes, status_store.MAX_OBJECT_BYTES)
        self.assertLess(state_bytes, status_store.MAX_OBJECT_BYTES)
        self.assertLess(max(intent_bytes, state_bytes), 4096)


if __name__ == "__main__":
    unittest.main(verbosity=2)
