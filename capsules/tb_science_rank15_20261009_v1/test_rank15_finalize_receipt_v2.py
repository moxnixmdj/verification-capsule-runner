from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rank15_finalize_receipt_v2 as finalizer


SAFE_ID = "protein-active-learning-trial-0"


class Rank15FinalizeReceiptV2Tests(unittest.TestCase):
    def _run(self, *, harbor_outcome: str, carrier_ready: bool, reward=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = {
                "task_read": harbor_outcome in {"success", "failure"},
                "pass": harbor_outcome in {"success", "failure"},
                "status": "PASS" if harbor_outcome in {"success", "failure"} else "NOT_RUN",
                "input_tokens": 100,
                "context_headroom_tokens": 12000,
            }
            (root / "RANK15_PRESTART_GUARD.json").write_text(
                json.dumps(guard), encoding="utf-8"
            )
            if reward is not None:
                p = root / "jobs" / SAFE_ID / "trial" / "result.json"
                p.parent.mkdir(parents=True)
                p.write_text(json.dumps({
                    "verifier_result": {"rewards": {"reward": reward}}
                }), encoding="utf-8")
            env = {
                "GITHUB_WORKSPACE": str(root),
                "SAFE_ID": SAFE_ID,
                "CACHE_READY": "true" if carrier_ready else "false",
                "HARBOR_OUTCOME": harbor_outcome,
                "GITHUB_RUN_ID": "synthetic",
                "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_SHA": "0" * 40,
            }
            with patch.dict(os.environ, env, clear=False):
                self.assertEqual(finalizer.main(), 0)
            return json.loads(
                (root / (SAFE_ID + "__SLOT_RECEIPT_V2.json")).read_text()
            )

    def test_success_is_slot_evidence_not_aggregate_acceptance_credit(self):
        out = self._run(harbor_outcome="success", carrier_ready=True, reward=1.0)
        self.assertEqual(out["status"], "SUCCESS")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 1)
        self.assertEqual(out["consumed_final_failures_delta"], 0)
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_started_non_success_is_irreversible_slot_failure_only(self):
        out = self._run(harbor_outcome="failure", carrier_ready=True, reward=0.0)
        self.assertEqual(out["status"], "FINAL_ZERO")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 1)
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_preexposure_abort_consumes_nothing(self):
        out = self._run(harbor_outcome="skipped", carrier_ready=False)
        self.assertEqual(out["status"], "PREEXPOSURE_ABORT_NONCONSUMING")
        self.assertEqual(out["benchmark_trials_consumed"], 0)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 0)
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
