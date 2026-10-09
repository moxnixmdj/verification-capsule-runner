from __future__ import annotations

import os
from pathlib import Path
import unittest

from execution_guard.logical_attempt_identity_v1 import logical_attempt_id
from canonical.runtime import harbor_science_agent_v9 as agent
from canonical.runtime import harbor_science_planner_v4 as planner
import rank16_v6_status_journal_runner as runner

SLOT = "terminal-bench-science/sparse-network-assimilation::trial-0"
DIGEST = "sha256:52ba7089dc32952df08c478af76b732fa82468c125431388adbf9798d869826f"
EXPECTED = logical_attempt_id(slot_id=SLOT, task_digest=DIGEST)


class Rank15V6RuntimeCompositionTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(os.environ)
        os.environ["BRAIN_SLOT_ID"] = SLOT
        os.environ["BRAIN_TASK_DIGEST"] = DIGEST
        os.environ["BRAIN_LOGICAL_ATTEMPT_ID"] = EXPECTED

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved)

    def test_goal_text_cannot_change_logical_attempt_identity(self):
        self.assertEqual(agent.logical_attempt_id_for_goal("alpha"), EXPECTED)
        self.assertEqual(agent.logical_attempt_id_for_goal("completely different text"), EXPECTED)

    def test_carried_identity_mismatch_fails_closed(self):
        os.environ["BRAIN_LOGICAL_ATTEMPT_ID"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"):
            agent.logical_attempt_id_for_goal("alpha")

    def test_runner_strips_credentials_and_carries_exact_identity(self):
        os.environ["GH_TOKEN"] = "must-not-cross"
        os.environ["GITHUB_TOKEN"] = "must-not-cross"
        child = runner._child_env()
        self.assertNotIn("GH_TOKEN", child)
        self.assertNotIn("GITHUB_TOKEN", child)
        self.assertEqual(child["BRAIN_LOGICAL_ATTEMPT_ID"], EXPECTED)
        self.assertEqual(child["BRAIN_SLOT_ID"], SLOT)
        self.assertEqual(child["BRAIN_TASK_DIGEST"], DIGEST)

    def test_runner_uses_v8_agent(self):
        os.environ["TASK_PATH"] = "/tmp/frozen-task"
        command = runner._harbor_command()
        self.assertIn("canonical.runtime.harbor_science_agent_v9:HarborScienceAgent", command)
        self.assertEqual(command[command.index("-r") + 1], "0")

    def test_planner_seed_serialization_is_bounded(self):
        for cycle in (0, 1, 11):
            payload, meta = planner.build_request_payload(
                "Return a tool call.",
                logical_attempt_id=EXPECTED,
                cycle=cycle,
            )
            self.assertEqual(meta["logical_attempt_id"], EXPECTED)
            self.assertLessEqual(len(str(meta["seed"])), 10)
            self.assertEqual(payload["seed"], meta["seed"])

    def test_start_cas_binds_complete_causal_runtime(self):
        source = Path(__file__).with_name("rank16_start_cas_v6.py").read_text(encoding="utf-8")
        for label in (
            '"identity_primitive"',
            '"start_barrier"',
            '"causal_journal"',
            '"causal_journal_bridge"',
            '"status_journal_runner"',
        ):
            self.assertIn(label, source)
        self.assertIn("PRESTART_LOGICAL_ATTEMPT_ID_NOT_SLOT_BOUND", source)

    def test_agent_has_durable_intent_and_state_commit(self):
        source = Path(agent.__file__).read_text(encoding="utf-8")
        intent = source.index('"PLANNER_PROPOSAL_ACTION_INTENT"')
        effect = source.index("await transport.exec(", intent)
        commit = source.index('"ACTION_VERIFY_STATE_COMMIT"', effect)
        self.assertLess(intent, effect)
        self.assertLess(effect, commit)
        self.assertIn("effect_replay_authority", source)

    def test_no_activation_file_exists_in_candidate(self):
        activation = Path(__file__).resolve().parents[2] / "ACTIVATE_RANK16_V1_PR.json"
        self.assertFalse(activation.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
