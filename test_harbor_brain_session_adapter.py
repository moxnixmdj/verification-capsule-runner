from __future__ import annotations

import asyncio
import importlib.metadata
import os
from pathlib import Path
import tempfile
import unittest

from harbor.agents.base import BaseAgent
from harbor.environments.base import ExecResult
from harbor.models.agent.context import AgentContext

from canonical.runtime.harbor_brain_session_agent import (
    BrainHarborSessionAgent,
    BrainHarborSessionError,
    _validate_authorization,
)


SESSION = "SYNTHETIC-HARBOR-SESSION"


class FakeEnvironment:
    def __init__(self):
        self.commands = []

    async def exec(self, command, **kwargs):
        self.commands.append((command, kwargs))
        if command == "printf SYNTHETIC_HARBOR_OK":
            return ExecResult(
                stdout="SYNTHETIC_HARBOR_OK",
                stderr="",
                return_code=0,
            )
        return ExecResult(stdout="", stderr="", return_code=0)


class HarborBrainSessionAdapterTests(unittest.TestCase):
    def test_exact_harbor_release(self):
        self.assertEqual(importlib.metadata.version("harbor"), "0.23.0")
        self.assertTrue(issubclass(BrainHarborSessionAgent, BaseAgent))
        self.assertEqual(
            BrainHarborSessionAgent.import_path(),
            "canonical.runtime.harbor_brain_session_agent:BrainHarborSessionAgent",
        )

    def test_fail_closed_terminal_authorization(self):
        bad = {
            "schema": "BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
            "session_id": SESSION,
            "submission_authorized": True,
            "known_relevant_failures": ["synthetic unresolved failure"],
            "acceptance_criteria": [
                {"criterion": "x", "status": "PASS", "evidence": "synthetic"}
            ],
            "verification_commands": [
                {"command": "true", "exit_code": 0}
            ],
        }
        with self.assertRaisesRegex(
            BrainHarborSessionError, "KNOWN_RELEVANT_FAILURES_REMAIN"
        ):
            _validate_authorization(bad, SESSION)

    def test_real_git_command_fetch_transport_and_authorized_finish(self):
        async def run():
            branch = os.environ.get("GITHUB_HEAD_REF")
            self.assertTrue(branch)
            with tempfile.TemporaryDirectory() as td:
                env = FakeEnvironment()
                ctx = AgentContext()
                agent = BrainHarborSessionAgent(
                    logs_dir=Path(td),
                    control_repo=Path.cwd(),
                    control_branch=branch,
                    poll_interval_sec=0.05,
                    command_wait_timeout_sec=30,
                    max_steps=4,
                )
                agent.session_id = SESSION
                await agent.setup(env)
                instruction = (
                    "Synthetic Harbor prequalification instruction. "
                    "No benchmark task content."
                )
                await agent.run(instruction, env, ctx)

                self.assertEqual(
                    env.commands,
                    [("printf SYNTHETIC_HARBOR_OK", {"timeout_sec": 30})],
                )
                meta = ctx.metadata["project_brain_harbor_session"]
                self.assertEqual(meta["status"], "AUTHORIZED_COMPLETE")
                self.assertEqual(meta["session_id"], SESSION)
                self.assertEqual(meta["completed_steps"], 2)
                self.assertTrue(meta["authorized"])

                root = Path(td) / "project_brain_harbor_session"
                self.assertTrue((root / "-01.json").is_file())
                self.assertTrue((root / "000.json").is_file())
                self.assertTrue((root / "001.json").is_file())

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
