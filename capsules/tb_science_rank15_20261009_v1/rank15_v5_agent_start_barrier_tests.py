from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v4 as agent


class Rank15V5AgentStartBarrierTests(unittest.IsolatedAsyncioTestCase):
    async def test_barrier_precedes_all_science_controller_work(self):
        events: list[str] = []

        async def barrier_call(logical_attempt_id: str):
            events.append("barrier")
            self.assertEqual(
                logical_attempt_id,
                agent.logical_attempt_id_for_goal("synthetic goal"),
            )
            return {"task_started": True}

        async def science_call(instruction, environment):
            events.append("science")
            self.assertEqual(instruction, "synthetic goal")
            return {"status": "synthetic"}

        with tempfile.TemporaryDirectory() as td:
            fake = SimpleNamespace(logs_dir=Path(td))
            context = SimpleNamespace(cost_usd=123.0)
            with patch.object(
                agent.start_barrier,
                "await_start_commit",
                new=AsyncMock(side_effect=barrier_call),
            ), patch.object(
                agent,
                "run_science_goal",
                new=AsyncMock(side_effect=science_call),
            ):
                await agent.HarborScienceAgent.run(
                    fake,
                    "synthetic goal",
                    object(),
                    context,
                )

            self.assertEqual(events, ["barrier", "science"])
            self.assertEqual(context.cost_usd, 0.0)
            self.assertTrue(
                (Path(td) / "project_brain_science_trace.json").is_file()
            )

    async def test_barrier_failure_prevents_controller_entry(self):
        with tempfile.TemporaryDirectory() as td:
            fake = SimpleNamespace(logs_dir=Path(td))
            context = SimpleNamespace(cost_usd=0.0)
            blocked = agent.start_barrier.AgentStartBarrierError(
                "START_COMMIT_TIMEOUT__NO_AGENT_ACTION"
            )
            with patch.object(
                agent.start_barrier,
                "await_start_commit",
                new=AsyncMock(side_effect=blocked),
            ), patch.object(
                agent,
                "run_science_goal",
                new=AsyncMock(),
            ) as science:
                with self.assertRaisesRegex(
                    agent.start_barrier.AgentStartBarrierError,
                    "NO_AGENT_ACTION",
                ):
                    await agent.HarborScienceAgent.run(
                        fake,
                        "synthetic goal",
                        object(),
                        context,
                    )

            science.assert_not_awaited()
            self.assertFalse(
                (Path(td) / "project_brain_science_trace.json").exists()
            )

    def test_method_shape_has_single_pre_action_barrier(self):
        source = inspect.getsource(agent.HarborScienceAgent.run)
        barrier_marker = "await start_barrier.await_start_commit(logical_attempt_id)"
        science_marker = "result = await run_science_goal(instruction, environment)"
        self.assertEqual(source.count(barrier_marker), 1)
        self.assertEqual(source.count(science_marker), 1)
        self.assertLess(source.index(barrier_marker), source.index(science_marker))
        self.assertNotIn("environment.", source[: source.index(barrier_marker)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
