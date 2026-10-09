from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from execution_guard import terminal_agent_start_barrier_v1 as barrier


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AgentStartBarrierTests(unittest.IsolatedAsyncioTestCase):
    def _env(self, root: Path) -> dict[str, str]:
        return {
            "BRAIN_AGENT_START_BARRIER_DIR": str(root / "barrier"),
            "BRAIN_SLOT_ID": "terminal-bench-science/example::trial-0",
            "BRAIN_TASK_DIGEST": "sha256:" + "1" * 64,
        }

    async def _wait_for_file(self, path: Path, timeout_s: float = 2.0) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        while not path.is_file():
            if loop.time() >= deadline:
                self.fail("timed out waiting for " + str(path))
            await asyncio.sleep(0.01)

    async def test_agent_cannot_cross_until_valid_start_commit_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._env(root)
            logical = "a" * 64
            with patch.dict(os.environ, env, clear=False):
                task = asyncio.create_task(
                    barrier.await_start_commit(logical, timeout_s=2.0, poll_s=0.01)
                )
                ready_path = root / "barrier/AGENT_READY.json"
                commit_path = root / "barrier/START_COMMITTED.json"
                await self._wait_for_file(ready_path)
                self.assertFalse(task.done())
                self.assertFalse(commit_path.exists())

                ready = json.loads(ready_path.read_text())
                cas_path = root / "cas.json"
                write_json(cas_path, {
                    "acquired": True,
                    "task_started": True,
                    "benchmark_trials_consumed": 1,
                    "slot_id": ready["slot_id"],
                    "task_digest": ready["task_digest"],
                    "logical_attempt_id": ready["logical_attempt_id"],
                    "agent_ready_receipt_sha256": sha256_file(ready_path),
                    "durable_record_sha256": "b" * 64,
                    "runtime_identity_sha256": "c" * 64,
                    "replay_authority": False,
                    "replacement_carrier_authority": False,
                })
                barrier.release_from_cas(
                    ready_path=ready_path,
                    cas_receipt_path=cas_path,
                    output_path=commit_path,
                )
                result = await task

            self.assertTrue(result["task_started"])
            self.assertEqual(result["logical_attempt_id"], logical)
            self.assertEqual(result["agent_ready_receipt_sha256"], sha256_file(ready_path))

    async def test_missing_commit_times_out_before_agent_action(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(os.environ, self._env(root), clear=False):
                with self.assertRaisesRegex(
                    barrier.AgentStartBarrierError,
                    "START_COMMIT_TIMEOUT__NO_AGENT_ACTION",
                ):
                    await barrier.await_start_commit(
                        "a" * 64,
                        timeout_s=0.05,
                        poll_s=0.01,
                    )
            ready = json.loads((root / "barrier/AGENT_READY.json").read_text())
            self.assertFalse(ready["task_started"])
            self.assertEqual(ready["benchmark_trials_consumed"], 0)

    async def test_wrong_commit_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._env(root)
            logical = "a" * 64
            with patch.dict(os.environ, env, clear=False):
                ready_path, ready, ready_sha = barrier.publish_ready(logical)
                write_json(root / "barrier/START_COMMITTED.json", {
                    "schema": barrier.COMMIT_SCHEMA,
                    "slot_id": ready["slot_id"],
                    "task_digest": ready["task_digest"],
                    "logical_attempt_id": "d" * 64,
                    "agent_ready_receipt_sha256": ready_sha,
                    "start_cas_receipt_sha256": "e" * 64,
                    "durable_start_record_sha256": "f" * 64,
                    "runtime_identity_sha256": "0" * 64,
                    "start_cas_acquired": True,
                    "task_started": True,
                    "benchmark_trials_consumed": 1,
                    "replay_authority": False,
                    "replacement_carrier_authority": False,
                })
                with self.assertRaisesRegex(
                    barrier.AgentStartBarrierError,
                    "START_COMMIT_INVALID:logical_attempt_id",
                ):
                    await barrier.await_start_commit(
                        logical,
                        timeout_s=0.2,
                        poll_s=0.01,
                    )
            self.assertTrue(ready_path.is_file())

    def test_release_rejects_unacquired_cas(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._env(root)
            logical = "a" * 64
            with patch.dict(os.environ, env, clear=False):
                ready_path, ready, ready_sha = barrier.publish_ready(logical)
                cas_path = root / "cas.json"
                write_json(cas_path, {
                    "acquired": False,
                    "task_started": False,
                    "benchmark_trials_consumed": 0,
                    "slot_id": ready["slot_id"],
                    "task_digest": ready["task_digest"],
                    "logical_attempt_id": ready["logical_attempt_id"],
                    "agent_ready_receipt_sha256": ready_sha,
                    "durable_record_sha256": "b" * 64,
                    "runtime_identity_sha256": "c" * 64,
                    "replay_authority": False,
                    "replacement_carrier_authority": False,
                })
                with self.assertRaisesRegex(
                    barrier.AgentStartBarrierError,
                    "START_CAS_NOT_ACQUIRED",
                ):
                    barrier.release_from_cas(
                        ready_path=ready_path,
                        cas_receipt_path=cas_path,
                        output_path=root / "barrier/START_COMMITTED.json",
                    )

    def test_release_is_idempotent_only_for_identical_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._env(root)
            logical = "a" * 64
            with patch.dict(os.environ, env, clear=False):
                ready_path, ready, ready_sha = barrier.publish_ready(logical)
                cas_path = root / "cas.json"
                write_json(cas_path, {
                    "acquired": True,
                    "task_started": True,
                    "benchmark_trials_consumed": 1,
                    "slot_id": ready["slot_id"],
                    "task_digest": ready["task_digest"],
                    "logical_attempt_id": ready["logical_attempt_id"],
                    "agent_ready_receipt_sha256": ready_sha,
                    "durable_record_sha256": "b" * 64,
                    "runtime_identity_sha256": "c" * 64,
                    "replay_authority": False,
                    "replacement_carrier_authority": False,
                })
                out = root / "barrier/START_COMMITTED.json"
                first = barrier.release_from_cas(
                    ready_path=ready_path,
                    cas_receipt_path=cas_path,
                    output_path=out,
                )
                second = barrier.release_from_cas(
                    ready_path=ready_path,
                    cas_receipt_path=cas_path,
                    output_path=out,
                )
                self.assertEqual(first, second)

                changed = json.loads(cas_path.read_text())
                changed["runtime_identity_sha256"] = "d" * 64
                write_json(cas_path, changed)
                with self.assertRaisesRegex(
                    barrier.AgentStartBarrierError,
                    "START_COMMIT_ALREADY_EXISTS_WITH_DIFFERENT_BYTES",
                ):
                    barrier.release_from_cas(
                        ready_path=ready_path,
                        cas_receipt_path=cas_path,
                        output_path=out,
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
