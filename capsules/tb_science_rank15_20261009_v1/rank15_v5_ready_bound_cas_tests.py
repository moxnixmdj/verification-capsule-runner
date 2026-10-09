from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rank15_start_cas_v5 as cas


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


class Rank15V5ReadyBoundCASTests(unittest.TestCase):
    def _fixture(self, root: Path, *, ready_logical: str = "a" * 64):
        guard = root / cas.PREFLIGHT_RECEIPT
        write_json(guard, {
            "pass": True,
            "status": "PASS__RANK15_V3_EXACT_TASK_READ__MAXIMAL_RESERVED_CYCLE0_CORE_FITS__TASK_NOT_STARTED",
            "task_read": True,
            "task_started": False,
            "task_digest": cas.TASK_DIGEST,
            "logical_attempt_id": "a" * 64,
            "payload_sha256": "1" * 64,
            "request_identity_sha256": "2" * 64,
        })

        ready = root / cas.AGENT_READY_REL
        write_json(ready, {
            "schema": "PROJECT_BRAIN_AGENT_START_READY_V1",
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
            "logical_attempt_id": ready_logical,
            "pid": 123,
            "task_started": False,
            "benchmark_trials_consumed": 0,
        })

        workflow = root / "workflow.yml"
        workflow.write_text("workflow-v5\n", encoding="utf-8")
        authority = root / "authority.json"
        write_json(authority, {"authority": "synthetic"})
        activation = root / "activation.json"
        write_json(activation, {"activate": True})

        surface = {
            "workflow_path": "workflow.yml",
            "workflow_git_blob_sha": git_blob(workflow),
            "authority": {
                "path": "authority.json",
                "git_blob_sha": git_blob(authority),
            },
        }
        context = {
            "surface": surface,
            "activation_path": activation,
        }
        return guard, ready, context

    def test_start_intent_binds_exact_ready_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _guard, ready, context = self._fixture(root)
            env = {
                "GITHUB_RUN_ID": "12345",
                "GITHUB_SHA": "f" * 40,
            }
            with patch.dict(os.environ, env, clear=False), patch.object(
                cas,
                "_runtime_identity",
                return_value=("b" * 64, {"synthetic": True}),
            ):
                intent, binding = cas._build_start_intent(root, context)

            ready_sha = hashlib.sha256(ready.read_bytes()).hexdigest()
            self.assertEqual(intent.agent_ready_receipt_sha256, ready_sha)
            self.assertEqual(binding["agent_ready_receipt_sha256"], ready_sha)
            self.assertEqual(intent.logical_attempt_id, "a" * 64)

    def test_missing_ready_receipt_fails_before_start_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _guard, ready, context = self._fixture(root)
            ready.unlink()
            with patch.dict(
                os.environ,
                {"GITHUB_RUN_ID": "12345", "GITHUB_SHA": "f" * 40},
                clear=False,
            ), patch.object(
                cas,
                "_runtime_identity",
                return_value=("b" * 64, {"synthetic": True}),
            ):
                with self.assertRaisesRegex(cas.StartCASError, "AGENT_READY_RECEIPT_MISSING"):
                    cas._build_start_intent(root, context)

    def test_ready_logical_attempt_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _guard, _ready, context = self._fixture(root, ready_logical="c" * 64)
            with patch.dict(
                os.environ,
                {"GITHUB_RUN_ID": "12345", "GITHUB_SHA": "f" * 40},
                clear=False,
            ), patch.object(
                cas,
                "_runtime_identity",
                return_value=("b" * 64, {"synthetic": True}),
            ):
                with self.assertRaisesRegex(cas.StartCASError, "AGENT_READY_LOGICAL_ATTEMPT_MISMATCH"):
                    cas._build_start_intent(root, context)

    def test_ready_claiming_started_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _guard, ready, context = self._fixture(root)
            value = json.loads(ready.read_text())
            value["task_started"] = True
            value["benchmark_trials_consumed"] = 1
            write_json(ready, value)
            with patch.dict(
                os.environ,
                {"GITHUB_RUN_ID": "12345", "GITHUB_SHA": "f" * 40},
                clear=False,
            ), patch.object(
                cas,
                "_runtime_identity",
                return_value=("b" * 64, {"synthetic": True}),
            ):
                with self.assertRaisesRegex(cas.StartCASError, "AGENT_READY_PRESTART_ACCOUNTING_INVALID"):
                    cas._build_start_intent(root, context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
