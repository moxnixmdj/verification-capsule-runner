from __future__ import annotations

import asyncio
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import importlib.metadata

from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial

import rank15_agent_start_cas_plugin_v1 as plugin_mod


class FakeJob:
    def __init__(self):
        self.callback = None

    def on_agent_started(self, callback):
        self.callback = callback
        return self


def event(task_name="terminal-bench-science/protein-active-learning"):
    return SimpleNamespace(
        event=TrialEvent.AGENT_START,
        task_name=task_name,
        trial_name="protein-active-learning__trial0",
        trial_id="00000000-0000-0000-0000-000000000001",
    )


class Rank15AgentStartCASPluginTests(unittest.TestCase):
    def _env(self, root: Path, runner_temp: Path) -> dict[str, str]:
        return {
            "GITHUB_WORKSPACE": str(root),
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_RUN_ID": "synthetic",
            "GITHUB_SHA": "1" * 40,
        }

    def _plugin(self, token_file: Path, root: Path):
        return plugin_mod.Rank15AgentStartCASPlugin(
            token_path=str(token_file),
            cas_script=str(root / "rank15_start_cas_v3.py"),
        )

    def test_harbor_version_and_lifecycle_place_agent_start_after_prepare(self):
        self.assertEqual(importlib.metadata.version("harbor"), "0.23.0")
        run_src = inspect.getsource(Trial.run)
        self.assertLess(run_src.index("await self._prepare()"), run_src.index("await self._run()"))
        phase_src = inspect.getsource(Trial._run_agent_phase)
        emit = phase_src.index("await self._emit(TrialEvent.AGENT_START)")
        context = phase_src.index("target.agent_result = AgentContext()")
        self.assertLess(emit, context)
        self.assertIn("await running_agent.run(", phase_src)
        self.assertLess(emit, phase_src.index("await running_agent.run("))

    def test_on_job_start_registers_only_agent_start_callback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "workspace"
            runner = Path(td) / "runner-temp"
            root.mkdir()
            runner.mkdir()
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            job = FakeJob()
            p = self._plugin(token_file, root)
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                asyncio.run(p.on_job_start(job))
            self.assertIsNotNone(job.callback)
            self.assertEqual(job.callback, p._on_agent_started)
            self.assertFalse(p._fired)

    def test_host_token_env_must_be_absent_before_harbor_plugin_start(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "workspace"
            runner = Path(td) / "runner-temp"
            root.mkdir()
            runner.mkdir()
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            p = self._plugin(token_file, root)
            env = self._env(root, runner)
            env["GH_TOKEN"] = "must-not-remain"
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaisesRegex(
                    plugin_mod.AgentStartCASError,
                    "REPOSITORY_WRITE_TOKEN_PRESENT_IN_HARBOR_HOST_ENV",
                ):
                    asyncio.run(p.on_job_start(FakeJob()))

    def test_token_file_must_be_runner_temp_and_outside_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            token_file = root / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            p = self._plugin(token_file, root)
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                with self.assertRaisesRegex(
                    plugin_mod.AgentStartCASError,
                    "TOKEN_PATH_MUST_BE_UNDER_RUNNER_TEMP",
                ):
                    p._consume_token_file()

    def test_token_file_requires_0600_or_stricter(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o644)
            p = self._plugin(token_file, root)
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                with self.assertRaisesRegex(
                    plugin_mod.AgentStartCASError,
                    "TOKEN_FILE_PERMISSIONS_TOO_BROAD",
                ):
                    p._consume_token_file()

    def test_agent_start_consumes_token_then_commits_cas_before_return(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            cas_script = root / "rank15_start_cas_v3.py"
            cas_script.write_text("# synthetic\n", encoding="utf-8")
            token_file = runner / "token"
            token_file.write_text("top-secret", encoding="utf-8")
            token_file.chmod(0o600)

            p = plugin_mod.Rank15AgentStartCASPlugin(
                token_path=str(token_file),
                cas_script=str(cas_script),
            )
            seen = {}

            def fake_run(token: str):
                seen["token"] = token
                seen["file_exists_during_subprocess"] = token_file.exists()
                seen["host_gh_token"] = os.environ.get("GH_TOKEN")
                (root / "RANK15_START_CAS_V3.json").write_text(
                    json.dumps(
                        {
                            "pass": True,
                            "acquired": True,
                            "task_started": True,
                            "slot_id": plugin_mod.EXPECTED_SLOT,
                            "task_digest": plugin_mod.EXPECTED_DIGEST,
                            "generic_cas_key": "terminal-start/" + "a" * 64,
                            "logical_attempt_id": "b" * 64,
                            "runtime_identity_sha256": "c" * 64,
                            "prestart_receipt_sha256": "d" * 64,
                            "durable_record_sha256": "e" * 64,
                            "replay_authority": False,
                            "replacement_carrier_authority": False,
                        }
                    ),
                    encoding="utf-8",
                )
                return 0, '{"ok":true}', ""

            p._run_cas_subprocess = fake_run
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                asyncio.run(p._on_agent_started(event()))

            self.assertEqual(seen["token"], "top-secret")
            self.assertFalse(seen["file_exists_during_subprocess"])
            self.assertIsNone(seen["host_gh_token"])
            self.assertFalse(token_file.exists())
            out = json.loads((root / plugin_mod.DEFAULT_RECEIPT).read_text())
            self.assertTrue(out["pass"])
            self.assertTrue(out["task_started"])
            self.assertTrue(out["token_file_deleted_before_cas_subprocess"])
            self.assertTrue(out["host_repository_token_env_absent"])

    def test_failed_cas_raises_before_hook_returns(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            cas_script = root / "rank15_start_cas_v3.py"
            cas_script.write_text("# synthetic\n", encoding="utf-8")
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            p = plugin_mod.Rank15AgentStartCASPlugin(
                token_path=str(token_file),
                cas_script=str(cas_script),
            )
            p._run_cas_subprocess = lambda token: (1, "", "failed")
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                with self.assertRaisesRegex(
                    plugin_mod.AgentStartCASError,
                    "DURABLE_START_CAS_NOT_CONFIRMED_BEFORE_AGENT_EXECUTION",
                ):
                    asyncio.run(p._on_agent_started(event()))
            self.assertFalse(token_file.exists())
            out = json.loads((root / plugin_mod.DEFAULT_RECEIPT).read_text())
            self.assertFalse(out["pass"])
            self.assertFalse(out["task_started"])

    def test_wrong_task_fails_before_token_consumption(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            p = self._plugin(token_file, root)
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                with self.assertRaisesRegex(plugin_mod.AgentStartCASError, "TASK_NAME_MISMATCH"):
                    asyncio.run(p._on_agent_started(event("wrong-task")))
            self.assertTrue(token_file.exists())

    def test_second_agent_start_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "workspace"
            runner = base / "runner-temp"
            root.mkdir()
            runner.mkdir()
            cas_script = root / "rank15_start_cas_v3.py"
            cas_script.write_text("# synthetic\n", encoding="utf-8")
            token_file = runner / "token"
            token_file.write_text("secret", encoding="utf-8")
            token_file.chmod(0o600)
            p = plugin_mod.Rank15AgentStartCASPlugin(
                token_path=str(token_file),
                cas_script=str(cas_script),
            )

            def fake_run(token: str):
                (root / "RANK15_START_CAS_V3.json").write_text(
                    json.dumps(
                        {
                            "pass": True,
                            "acquired": True,
                            "task_started": True,
                            "slot_id": plugin_mod.EXPECTED_SLOT,
                            "task_digest": plugin_mod.EXPECTED_DIGEST,
                            "replay_authority": False,
                            "replacement_carrier_authority": False,
                        }
                    ),
                    encoding="utf-8",
                )
                return 0, "", ""

            p._run_cas_subprocess = fake_run
            with patch.dict(os.environ, self._env(root, runner), clear=False):
                asyncio.run(p._on_agent_started(event()))
                with self.assertRaisesRegex(
                    plugin_mod.AgentStartCASError,
                    "AGENT_START_HOOK_FIRED_MORE_THAN_ONCE",
                ):
                    asyncio.run(p._on_agent_started(event()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
