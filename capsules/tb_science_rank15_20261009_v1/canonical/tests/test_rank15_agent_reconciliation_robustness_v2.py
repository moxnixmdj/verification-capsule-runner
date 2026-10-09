from __future__ import annotations
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v6 as agent


class AgentReconciliationTests(unittest.IsolatedAsyncioTestCase):
    async def test_uncertain_effect_reconciles_without_replay(self):
        calls = []
        class Env:
            async def exec(self, command, timeout_sec=None, **kwargs):
                calls.append(command)
                if command == "effect_once":
                    raise RuntimeError("receipt lost")
                if command == "verify_once":
                    return SimpleNamespace(returncode=0, stdout="proved", stderr="")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        def plan(*args, **kwargs):
            return {
                "text": json.dumps({
                    "material_requirements": ["R1"],
                    "candidates": [{
                        "action_id": "A1",
                        "covers": ["R1"],
                        "command": "effect_once",
                        "verify_command": "verify_once"
                    }]
                }),
                "model": "synthetic"
            }

        with patch.object(agent.science_planner, "plan", plan), patch.object(
            agent.science_planner, "count_input_tokens", lambda payload: 1000
        ):
            out = await agent.run_science_goal("Create result.", Env(), max_cycles=1)

        self.assertEqual(calls.count("effect_once"), 1)
        self.assertEqual(calls.count("verify_once"), 1)
        row = [x for x in out["trace"] if x.get("kind") == "BRAIN_SELECTED_RESEARCH_ACTION"][0]
        self.assertFalse(row["effect_replayed"])
        self.assertTrue(row["uncertain_action_reconciled_by_existing_verifier"])
        self.assertEqual(out["resolved_requirements"], ["R1"])

    async def test_unreconciled_uncertainty_blocks_without_replay(self):
        calls = []
        class Env:
            async def exec(self, command, timeout_sec=None, **kwargs):
                calls.append(command)
                if command == "effect_once":
                    raise RuntimeError("receipt lost")
                if command == "verify_once":
                    return SimpleNamespace(returncode=1, stdout="", stderr="not proved")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        def plan(*args, **kwargs):
            return {
                "text": json.dumps({
                    "material_requirements": ["R1"],
                    "candidates": [{
                        "action_id": "A1",
                        "covers": ["R1"],
                        "command": "effect_once",
                        "verify_command": "verify_once"
                    }]
                }),
                "model": "synthetic"
            }

        with patch.object(agent.science_planner, "plan", plan), patch.object(
            agent.science_planner, "count_input_tokens", lambda payload: 1000
        ):
            out = await agent.run_science_goal("Create result.", Env(), max_cycles=1)

        self.assertEqual(calls.count("effect_once"), 1)
        self.assertEqual(calls.count("verify_once"), 1)
        self.assertEqual(out["status"], "BLOCKED_ACTION_EFFECT_OUTCOME_UNCERTAIN")
        self.assertFalse(out["effect_replay_authority"])
        self.assertEqual(out["resolved_requirements"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
