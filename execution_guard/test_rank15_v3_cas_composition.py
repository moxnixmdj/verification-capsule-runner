from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "execution_guard"))
sys.path.insert(0, str(ROOT / "capsules/tb_science_rank15_20261009_v1"))

import terminal_execution_admission_v2 as admission
import terminal_slot_start_cas_v1 as start_cas
import rank15_finalize_receipt_v3 as finalizer

WORKFLOW = ROOT / ".github/workflows/execute-tb-science-rank15-20261009-v3.yml"
BEHAVIOR = ROOT / "execution_guard/TB_SCIENCE_RANK15_EXECUTION_BEHAVIOR_V3.json"
INVARIANTS = ROOT / "execution_guard/CURRENT_VERIFIED_EXECUTION_INVARIANTS_V1.json"
ALL_CYCLE = ROOT / "execution_guard/TB_SCIENCE_RANK15_V3_ALL_CYCLE_ENVELOPE_VERIFICATION_20261009_V1.json"


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    import hashlib
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class CompositionTests(unittest.TestCase):
    def test_workflow_composition_is_exactly_ordered(self):
        errors = admission.check_rank15_v3_workflow_text(WORKFLOW.read_text())
        self.assertEqual(errors, [])

    def test_behavior_preserves_active_verified_invariants(self):
        behavior = json.loads(BEHAVIOR.read_text())
        invariants = json.loads(INVARIANTS.read_text())
        self.assertEqual(admission.check_behavior_against_invariants(behavior, invariants), [])
        errors = []
        admission.check_runtime_bindings(behavior, errors)
        self.assertEqual(errors, [])

    def test_all_cycle_proof_is_content_bound(self):
        behavior = json.loads(BEHAVIOR.read_text())
        proof = behavior["proofs"]["all_cycle_envelope"]
        self.assertEqual(proof["path"], str(ALL_CYCLE.relative_to(ROOT)))
        self.assertEqual(proof["git_blob_sha"], git_blob(ALL_CYCLE))
        doc = json.loads(ALL_CYCLE.read_text())
        self.assertIn("ALL_CYCLE_CONTEXT_ENVELOPE_BY_CONSTRUCTION", doc["status"])
        self.assertFalse(doc["execution_authority"])

    def test_staging_surface_has_no_activation_file(self):
        self.assertFalse(
            (ROOT / "capsules/tb_science_rank15_20261009_v1/ACTIVATE_RANK15_V3_PR.json").exists()
        )
        behavior = json.loads(BEHAVIOR.read_text())
        self.assertFalse(behavior["execution_authority"])
        self.assertEqual(behavior["terminal_benchmark_task_exposure"], 0)
        self.assertEqual(behavior["benchmark_trials_executed"], 0)

    def test_cas_key_is_global_per_slot_not_carrier(self):
        a = start_cas.slot_start_key(finalizer.SLOT, finalizer.DIGEST)
        b = start_cas.slot_start_key(finalizer.SLOT, finalizer.DIGEST)
        self.assertEqual(a, b)
        self.assertNotIn("run", a)

    def _synthetic_root(self, *, cas: bool, reward: float | None = 1.0):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        (root / "jobs/protein-active-learning-trial-0/t0").mkdir(parents=True)
        result = {
            "verifier_result": {
                "rewards": {"reward": reward}
            }
        } if reward is not None else {}
        (root / "jobs/protein-active-learning-trial-0/t0/result.json").write_text(
            json.dumps(result)
        )
        (root / "RANK15_PRESTART_GUARD.json").write_text(
            json.dumps(
                {
                    "pass": True,
                    "task_read": True,
                    "task_started": False,
                    "status": "PASS",
                    "logical_attempt_id": "a" * 64,
                    "payload_sha256": "b" * 64,
                    "input_tokens": 1000,
                    "context_headroom_tokens": 11288,
                }
            )
        )
        (root / "RANK15_START_INTENT.json").write_text(
            json.dumps({"slot_id": finalizer.SLOT, "task_digest": finalizer.DIGEST})
        )
        if cas:
            (root / "TERMINAL_SLOT_START_CAS_RECEIPT.json").write_text(
                json.dumps(
                    {
                        "status": "TASK_START_INTENT_COMMITTED",
                        "key": "terminal-start/" + "c" * 64,
                        "replay_authority": False,
                        "replacement_carrier_authority": False,
                    }
                )
            )
        surface = root / finalizer.SURFACE
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text(
            json.dumps(
                {
                    "workflow_path": finalizer.WORKFLOW,
                    "slot_id": finalizer.SLOT,
                    "task_digest": finalizer.DIGEST,
                    "execution_authority": True,
                }
            )
        )
        return td, root

    def test_single_slot_success_never_mints_aggregate_acceptance_credit(self):
        td, root = self._synthetic_root(cas=True, reward=1.0)
        try:
            receipt = finalizer.build_receipt(
                root,
                {
                    "SAFE_ID": "protein-active-learning-trial-0",
                    "HARBOR_OUTCOME": "success",
                    "CARRIER_READY": "true",
                },
            )
            self.assertEqual(receipt["status"], "SUCCESS")
            self.assertTrue(receipt["slot_success_evidence"])
            self.assertTrue(receipt["task_start_intent_committed"])
            self.assertEqual(receipt["benchmark_trials_consumed"], 1)
            self.assertEqual(receipt["acceptance_credit_delta"], 0)
            self.assertFalse(receipt["promotion_authority"])
            self.assertFalse(receipt["rerun_credit"])
        finally:
            td.cleanup()

    def test_started_without_cas_cannot_be_success(self):
        td, root = self._synthetic_root(cas=False, reward=1.0)
        try:
            receipt = finalizer.build_receipt(
                root,
                {
                    "SAFE_ID": "protein-active-learning-trial-0",
                    "HARBOR_OUTCOME": "success",
                    "CARRIER_READY": "true",
                },
            )
            self.assertEqual(receipt["status"], "FINAL_ZERO")
            self.assertFalse(receipt["slot_success_evidence"])
            self.assertIn("TASK_STARTED_WITHOUT_DURABLE_START_CAS", receipt["errors"])
            self.assertEqual(receipt["acceptance_credit_delta"], 0)
        finally:
            td.cleanup()

    def test_preexposure_cas_absence_is_nonconsuming(self):
        td, root = self._synthetic_root(cas=False, reward=None)
        try:
            receipt = finalizer.build_receipt(
                root,
                {
                    "SAFE_ID": "protein-active-learning-trial-0",
                    "HARBOR_OUTCOME": "skipped",
                    "CARRIER_READY": "true",
                },
            )
            self.assertEqual(receipt["status"], "PREEXPOSURE_ABORT_NONCONSUMING")
            self.assertEqual(receipt["benchmark_trials_consumed"], 0)
            self.assertFalse(receipt["execution_authority_consumed"])
            self.assertEqual(receipt["acceptance_credit_delta"], 0)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
