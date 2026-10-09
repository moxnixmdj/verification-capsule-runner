from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rank15_start_cas_v3 as cas
import rank15_finalize_receipt_v3 as finalizer

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/execute-tb-science-rank15-20261009-v3.yml"


class Rank15V3StartCASTests(unittest.TestCase):
    def _workspace(self, root: Path) -> dict[str, str]:
        activation = root / cas.ACTIVATION_REL
        activation.parent.mkdir(parents=True, exist_ok=True)
        activation.write_text(json.dumps({
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V3",
            "activate": True,
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
        }), encoding="utf-8")
        surface = root / cas.SURFACE_REL
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text(json.dumps({
            "execution_authority": True,
            "task_started": False,
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
        }), encoding="utf-8")
        event = root / "event.json"
        event.write_text(json.dumps({
            "pull_request": {
                "head": {
                    "ref": cas.EXPECTED_HEAD,
                    "repo": {"full_name": cas.EXPECTED_REPOSITORY},
                },
                "base": {"ref": cas.EXPECTED_BASE},
            }
        }), encoding="utf-8")
        return {
            "GITHUB_WORKSPACE": str(root),
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_BASE_REF": cas.EXPECTED_BASE,
            "GITHUB_HEAD_REF": cas.EXPECTED_HEAD,
            "GITHUB_REPOSITORY": cas.EXPECTED_REPOSITORY,
            "GITHUB_EVENT_PATH": str(event),
            "GITHUB_SHA": "1" * 40,
        }

    def test_pre_task_read_check_passes_only_when_lock_absent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            with patch.dict(os.environ, env, clear=False), patch.object(
                cas, "_api", return_value=(404, {"message": "Not Found"})
            ), patch.object(sys, "argv", ["cas", "--check-absent"]):
                rc = cas.main()
            self.assertEqual(rc, 0)
            out = json.loads((root / cas.CHECK_RECEIPT).read_text())
            self.assertTrue(out["lock_absent"])
            self.assertFalse(out["acquired"])
            self.assertFalse(out["task_started"])
            self.assertEqual(out["benchmark_trials_consumed"], 0)

    def test_acquire_is_atomic_start_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            (root / cas.PREFLIGHT_RECEIPT).write_text(json.dumps({
                "pass": True,
                "status": "PASS__RANK15_V3_EXACT_TASK_READ__MAXIMAL_RESERVED_CYCLE0_CORE_FITS__TASK_NOT_STARTED",
                "task_read": True,
                "task_started": False,
                "task_digest": cas.TASK_DIGEST,
            }), encoding="utf-8")
            responses = [(404, {"message": "Not Found"}), (201, {"ref": cas.LOCK_REF})]
            with patch.dict(os.environ, env, clear=False), patch.object(
                cas, "_api", side_effect=responses
            ), patch.object(sys, "argv", ["cas", "--acquire"]):
                rc = cas.main()
            self.assertEqual(rc, 0)
            out = json.loads((root / cas.ACQUIRE_RECEIPT).read_text())
            self.assertTrue(out["acquired"])
            self.assertTrue(out["task_started"])
            self.assertEqual(out["benchmark_trials_consumed"], 1)
            self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_existing_lock_fails_closed_without_start(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            with patch.dict(os.environ, env, clear=False), patch.object(
                cas, "_api", return_value=(200, {"ref": cas.LOCK_REF})
            ), patch.object(sys, "argv", ["cas", "--acquire"]):
                rc = cas.main()
            self.assertEqual(rc, 1)
            out = json.loads((root / cas.ACQUIRE_RECEIPT).read_text())
            self.assertFalse(out["acquired"])
            self.assertFalse(out["task_started"])
            self.assertEqual(out["benchmark_trials_consumed"], 0)

    def _finalize(self, *, cas_acquired: bool, reward=None) -> dict:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "RANK15_PRESTART_GUARD.json").write_text(json.dumps({
            "pass": True,
            "status": "PASS__RANK15_V3_EXACT_TASK_READ__MAXIMAL_RESERVED_CYCLE0_CORE_FITS__TASK_NOT_STARTED",
            "task_read": True,
            "task_started": False,
            "task_digest": finalizer.DIGEST,
            "input_tokens": 7000,
        }), encoding="utf-8")
        if cas_acquired:
            (root / "RANK15_START_CAS_V3.json").write_text(json.dumps({
                "pass": True,
                "acquired": True,
                "task_started": True,
                "slot_id": finalizer.SLOT,
                "task_digest": finalizer.DIGEST,
                "status": "PASS__DURABLE_START_CAS_ACQUIRED__IRREVERSIBLE_SLOT_START",
                "lock_ref": cas.LOCK_REF,
                "lock_commit_sha": "1" * 40,
            }), encoding="utf-8")
        if reward is not None:
            p = root / "jobs/protein-active-learning-trial-0/trial/result.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({
                "verifier_result": {"rewards": {"reward": reward}}
            }), encoding="utf-8")
        env = {
            "GITHUB_WORKSPACE": str(root),
            "SAFE_ID": "protein-active-learning-trial-0",
            "CACHE_READY": "true",
            "HARBOR_OUTCOME": "success" if reward == 1.0 else "failure",
            "GITHUB_RUN_ID": "synthetic",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_SHA": "1" * 40,
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(finalizer.main(), 0)
        return json.loads(
            (root / "protein-active-learning-trial-0__SLOT_RECEIPT_V3.json").read_text()
        )

    def test_single_success_is_slot_evidence_not_aggregate_acceptance(self):
        out = self._finalize(cas_acquired=True, reward=1.0)
        self.assertEqual(out["status"], "SUCCESS")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 1)
        self.assertEqual(out["consumed_final_failures_delta"], 0)
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_cas_started_non_success_is_irreversible_final_zero(self):
        out = self._finalize(cas_acquired=True, reward=0.0)
        self.assertEqual(out["status"], "FINAL_ZERO")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 1)
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_no_cas_consumes_nothing_even_after_prestart_read(self):
        out = self._finalize(cas_acquired=False)
        self.assertEqual(out["status"], "PREEXPOSURE_ABORT_NONCONSUMING")
        self.assertEqual(out["benchmark_trials_consumed"], 0)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 0)
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_execution_workflow_orders_cas_between_prestart_and_harbor(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        markers = [
            "rank15_start_cas_v3.py --check-absent",
            "rank15_prestart_token_guard_v3.py",
            "rank15_start_cas_v3.py --acquire",
            "harbor run",
            "rank15_finalize_receipt_v3.py",
        ]
        positions = [text.index(x) for x in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(text.count("harbor run"), 1)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("rank15_prestart_token_guard_v2.py", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
