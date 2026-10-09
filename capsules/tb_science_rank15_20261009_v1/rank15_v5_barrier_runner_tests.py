from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rank15_v5_barrier_runner as runner


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


class FakeProc:
    def __init__(self, events, *, poll_value=None, wait_value=0):
        self.events = events
        self.poll_value = poll_value
        self.wait_value = wait_value
        self.terminated = False
        self.killed = False

    def poll(self):
        self.events.append("poll")
        return self.poll_value

    def wait(self, timeout=None):
        self.events.append("wait")
        return self.wait_value

    def terminate(self):
        self.events.append("terminate")
        self.terminated = True
        self.poll_value = -15

    def kill(self):
        self.events.append("kill")
        self.killed = True
        self.poll_value = -9


class Rank15V5BarrierRunnerTests(unittest.TestCase):
    def _patch_paths(self, root: Path):
        c = root / "capsules/tb_science_rank15_20261009_v1"
        c.mkdir(parents=True, exist_ok=True)
        return patch.multiple(
            runner,
            ROOT=root,
            C=c,
            CAS_RECEIPT=root / "RANK15_START_CAS_V5.json",
            RUNNER_RECEIPT=root / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json",
            HARBOR_LOG=root / "RANK15_V5_HARBOR_RUN.log",
        )

    def _env(self) -> dict[str, str]:
        return {
            "TASK_PATH": "/tmp/synthetic-task",
            "SAFE_ID": "protein-active-learning-trial-0",
            "GH_TOKEN": "parent-write-token",
            "GITHUB_TOKEN": "parent-write-token-2",
        }

    def test_success_orders_launch_ready_cas_release_wait_and_strips_child_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events = []
            captured = {}
            with self._patch_paths(root), patch.dict(os.environ, self._env(), clear=False):
                def popen_factory(command, **kwargs):
                    events.append("launch")
                    captured["command"] = command
                    captured["env"] = kwargs["env"]
                    ready = root / runner.READY_REL
                    write_json(ready, {"ready": True})
                    return FakeProc(events, wait_value=0)

                def acquire():
                    events.append("acquire")
                    write_json(root / "RANK15_START_CAS_V5.json", {
                        "acquired": True,
                        "task_started": True,
                    })

                def release():
                    events.append("release")
                    write_json(root / runner.COMMIT_REL, {"released": True})

                rc = runner.run_once(
                    popen_factory=popen_factory,
                    acquire_start=acquire,
                    release_agent=release,
                    sleep=lambda _: None,
                )

            self.assertEqual(rc, 0)
            self.assertEqual(events[0], "launch")
            self.assertLess(events.index("launch"), events.index("acquire"))
            self.assertLess(events.index("acquire"), events.index("release"))
            self.assertLess(events.index("release"), events.index("wait"))
            self.assertNotIn("GH_TOKEN", captured["env"])
            self.assertNotIn("GITHUB_TOKEN", captured["env"])
            self.assertIn("harbor_science_agent_v4:HarborScienceAgent", captured["command"])
            receipt = json.loads((root / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "HARBOR_COMPLETE")
            self.assertTrue(receipt["task_started"])
            self.assertEqual(receipt["benchmark_trials_consumed"], 1)
            self.assertTrue(receipt["agent_released"])

    def test_harbor_exit_before_ready_is_nonconsuming(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events = []
            called = {"acquire": False}
            with self._patch_paths(root), patch.dict(os.environ, self._env(), clear=False):
                def popen_factory(command, **kwargs):
                    events.append("launch")
                    return FakeProc(events, poll_value=17, wait_value=17)

                def acquire():
                    called["acquire"] = True

                rc = runner.run_once(
                    popen_factory=popen_factory,
                    acquire_start=acquire,
                    release_agent=lambda: None,
                    sleep=lambda _: None,
                )

            self.assertEqual(rc, 1)
            self.assertFalse(called["acquire"])
            receipt = json.loads((root / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "PRESTART_ABORT__NONCONSUMING")
            self.assertFalse(receipt["task_started"])
            self.assertEqual(receipt["benchmark_trials_consumed"], 0)

    def test_cas_failure_before_commit_never_releases_agent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events = []
            released = {"value": False}
            with self._patch_paths(root), patch.dict(os.environ, self._env(), clear=False):
                def popen_factory(command, **kwargs):
                    events.append("launch")
                    write_json(root / runner.READY_REL, {"ready": True})
                    return FakeProc(events)

                def acquire():
                    events.append("acquire")
                    raise RuntimeError("CAS unavailable before commit")

                def release():
                    released["value"] = True

                rc = runner.run_once(
                    popen_factory=popen_factory,
                    acquire_start=acquire,
                    release_agent=release,
                    sleep=lambda _: None,
                )

            self.assertEqual(rc, 1)
            self.assertFalse(released["value"])
            self.assertIn("terminate", events)
            receipt = json.loads((root / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "PRESTART_ABORT__NONCONSUMING")
            self.assertFalse(receipt["task_started"])

    def test_failure_after_confirmed_cas_is_irreversible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events = []
            with self._patch_paths(root), patch.dict(os.environ, self._env(), clear=False):
                def popen_factory(command, **kwargs):
                    events.append("launch")
                    write_json(root / runner.READY_REL, {"ready": True})
                    return FakeProc(events)

                def acquire():
                    events.append("acquire")
                    write_json(root / "RANK15_START_CAS_V5.json", {
                        "acquired": True,
                        "task_started": True,
                    })

                def release():
                    events.append("release")
                    raise RuntimeError("release failed after durable CAS")

                rc = runner.run_once(
                    popen_factory=popen_factory,
                    acquire_start=acquire,
                    release_agent=release,
                    sleep=lambda _: None,
                )

            self.assertEqual(rc, 1)
            receipt = json.loads((root / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "POSTSTART_ABORT__IRREVERSIBLE")
            self.assertTrue(receipt["task_started"])
            self.assertEqual(receipt["benchmark_trials_consumed"], 1)
            self.assertIn("terminate", events)


if __name__ == "__main__":
    unittest.main(verbosity=2)
