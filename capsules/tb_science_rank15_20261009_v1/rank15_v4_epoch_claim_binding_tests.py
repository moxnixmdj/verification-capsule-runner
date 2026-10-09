from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rank15_start_cas_v4 as cas
import rank15_finalize_receipt_v4 as finalizer


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return git_blob(path)


class Rank15V4EpochClaimBindingTests(unittest.TestCase):
    def _event_fixture(self, root: Path):
        activation = root / cas.ACTIVATION_REL
        write_json(activation, {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V4",
            "activate": True,
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
        })
        authority = root / "authority.json"
        write_json(authority, {})
        epoch = root / "epoch.json"
        epoch_blob = write_json(epoch, {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EPOCH_V4",
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
            "execution_branch": cas.EXPECTED_HEAD,
        })
        claim = root / "claim.json"
        claim_blob = write_json(claim, {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_CLAIM_V4",
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
            "execution_branch": cas.EXPECTED_HEAD,
            "activation_filename": "ACTIVATE_RANK15_V4_PR.json",
            "epoch_git_blob_sha": epoch_blob,
        })
        surface = root / cas.SURFACE_REL
        write_json(surface, {
            "execution_authority": True,
            "task_started": False,
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
            "authority": {"path": "authority.json", "git_blob_sha": git_blob(authority)},
            "epoch": {"path": "epoch.json", "git_blob_sha": epoch_blob},
            "execution_claim": {"path": "claim.json", "git_blob_sha": claim_blob},
        })
        event = root / "event.json"
        write_json(event, {
            "pull_request": {
                "head": {
                    "ref": cas.EXPECTED_HEAD,
                    "repo": {"full_name": cas.EXPECTED_REPOSITORY},
                },
                "base": {"ref": cas.EXPECTED_BASE},
            }
        })
        env = {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_BASE_REF": cas.EXPECTED_BASE,
            "GITHUB_HEAD_REF": cas.EXPECTED_HEAD,
            "GITHUB_REPOSITORY": cas.EXPECTED_REPOSITORY,
            "GITHUB_EVENT_PATH": str(event),
        }
        return env, epoch, claim

    def test_event_context_accepts_exact_epoch_claim_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env, _epoch, _claim = self._event_fixture(root)
            with patch.dict(os.environ, env, clear=False):
                out = cas._event_context(root)
        self.assertEqual(out["epoch"]["schema"], "PROJECT_BRAIN_TB_SCIENCE_RANK15_EPOCH_V4")
        self.assertEqual(out["execution_claim"]["epoch_git_blob_sha"], out["epoch_git_blob_sha"])

    def test_event_context_rejects_claim_bound_to_other_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env, _epoch, claim = self._event_fixture(root)
            value = json.loads(claim.read_text())
            value["epoch_git_blob_sha"] = "0" * 40
            claim_blob = write_json(claim, value)
            surface = json.loads((root / cas.SURFACE_REL).read_text())
            surface["execution_claim"]["git_blob_sha"] = claim_blob
            write_json(root / cas.SURFACE_REL, surface)
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaisesRegex(cas.StartCASError, "EXECUTION_CLAIM_EPOCH_BINDING_MISMATCH"):
                    cas._event_context(root)

    def test_runtime_identity_hash_changes_when_epoch_or_claim_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = root / "runtime.txt"
            runtime.write_text("runtime\n", encoding="utf-8")
            labels = (
                "planner", "agent", "prestart_guard", "transport", "zero_exposure_tests",
                "all_cycle_proof", "start_cas", "generic_start_cas", "generic_ref_store",
                "finalizer", "preflight", "admission_guard",
            )
            bindings = {
                label: {"path": "runtime.txt", "git_blob_sha": git_blob(runtime)}
                for label in labels
            }
            behavior = root / "behavior.json"
            behavior_blob = write_json(behavior, {"runtime_bindings": bindings})
            epoch = root / "epoch.json"
            epoch_blob = write_json(epoch, {"x": 1})
            claim = root / "claim.json"
            claim_blob = write_json(claim, {"x": 1})
            surface = {
                "behavior": {"path": "behavior.json", "git_blob_sha": behavior_blob},
                "epoch": {"path": "epoch.json", "git_blob_sha": epoch_blob},
                "execution_claim": {"path": "claim.json", "git_blob_sha": claim_blob},
            }
            digest1, material1 = cas._runtime_identity(root, surface)
            self.assertEqual(material1["epoch_git_blob_sha"], epoch_blob)
            self.assertEqual(material1["execution_claim_git_blob_sha"], claim_blob)

            claim_blob2 = write_json(claim, {"x": 2})
            surface["execution_claim"]["git_blob_sha"] = claim_blob2
            digest2, material2 = cas._runtime_identity(root, surface)
            self.assertNotEqual(digest1, digest2)
            self.assertEqual(material2["execution_claim_git_blob_sha"], claim_blob2)

    def test_finalizer_rejects_started_success_when_runtime_epoch_claim_binding_is_wrong(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "RANK15_PRESTART_GUARD.json"
            write_json(guard, {
                "pass": True,
                "status": "PASS__RANK15_V3_EXACT_TASK_READ__MAXIMAL_RESERVED_CYCLE0_CORE_FITS__TASK_NOT_STARTED",
                "task_read": True,
                "task_started": False,
                "logical_attempt_id": "a" * 64,
            })
            epoch = root / "epoch.json"
            epoch_blob = write_json(epoch, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EPOCH_V4"})
            claim = root / "claim.json"
            claim_blob = write_json(claim, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_CLAIM_V4"})
            write_json(root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json", {
                "epoch": {"path": "epoch.json", "git_blob_sha": epoch_blob},
                "execution_claim": {"path": "claim.json", "git_blob_sha": claim_blob},
            })
            write_json(root / "RANK15_START_CAS_V4.json", {
                "pass": True,
                "acquired": True,
                "task_started": True,
                "slot_id": finalizer.SLOT,
                "task_digest": finalizer.DIGEST,
                "generic_cas_key": finalizer._slot_start_key(),
                "logical_attempt_id": "a" * 64,
                "runtime_identity_sha256": "d" * 64,
                "runtime_identity_material": {
                    "epoch_git_blob_sha": "0" * 40,
                    "execution_claim_git_blob_sha": claim_blob,
                },
                "prestart_receipt_sha256": hashlib.sha256(guard.read_bytes()).hexdigest(),
                "durable_record_sha256": "1" * 64,
                "workflow_git_blob_sha": "2" * 40,
                "authority_git_blob_sha": "3" * 40,
                "activation_git_blob_sha": "4" * 40,
                "replay_authority": False,
                "replacement_carrier_authority": False,
            })
            result = root / "jobs/protein-active-learning-trial-0/trial/result.json"
            write_json(result, {"verifier_result": {"rewards": {"reward": 1.0}}})
            env = {
                "GITHUB_WORKSPACE": str(root),
                "SAFE_ID": "protein-active-learning-trial-0",
                "CACHE_READY": "true",
                "HARBOR_OUTCOME": "success",
            }
            with patch.dict(os.environ, env, clear=False):
                self.assertEqual(finalizer.main(), 0)
            out = json.loads(
                (root / "protein-active-learning-trial-0__SLOT_RECEIPT_V4.json").read_text()
            )
        self.assertEqual(out["status"], "FINAL_ZERO")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 1)
        self.assertTrue(any("RUNTIME_IDENTITY_EPOCH_MATCH" in x for x in out["errors"]))


    def test_finalizer_rejects_hash_shaped_noncurrent_runtime_and_surface_bindings(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "RANK15_PRESTART_GUARD.json"
            write_json(guard, {
                "pass": True,
                "task_read": True,
                "task_started": False,
                "logical_attempt_id": "a" * 64,
            })
            workflow = root / "workflow.yml"
            workflow.write_text("workflow-v4\n", encoding="utf-8")
            authority = root / "authority.json"
            write_json(authority, {"authority": "current"})
            activation = root / "activate.json"
            write_json(activation, {"activate": True})
            epoch = root / "epoch.json"
            epoch_blob = write_json(epoch, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EPOCH_V4"})
            claim = root / "claim.json"
            claim_blob = write_json(claim, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_CLAIM_V4"})
            write_json(root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json", {
                "workflow_path": "workflow.yml",
                "workflow_git_blob_sha": git_blob(workflow),
                "authority": {"path": "authority.json", "git_blob_sha": git_blob(authority)},
                "activation_path": "activate.json",
                "epoch": {"path": "epoch.json", "git_blob_sha": epoch_blob},
                "execution_claim": {"path": "claim.json", "git_blob_sha": claim_blob},
            })
            write_json(root / "RANK15_START_CAS_V4.json", {
                "pass": True,
                "acquired": True,
                "task_started": True,
                "slot_id": finalizer.SLOT,
                "task_digest": finalizer.DIGEST,
                "generic_cas_key": finalizer._slot_start_key(),
                "logical_attempt_id": "a" * 64,
                "runtime_identity_sha256": "d" * 64,
                "runtime_identity_material": {
                    "epoch_git_blob_sha": epoch_blob,
                    "execution_claim_git_blob_sha": claim_blob,
                },
                "prestart_receipt_sha256": hashlib.sha256(guard.read_bytes()).hexdigest(),
                "durable_record_sha256": "1" * 64,
                "workflow_git_blob_sha": "2" * 40,
                "authority_git_blob_sha": "3" * 40,
                "activation_git_blob_sha": "4" * 40,
                "replay_authority": False,
                "replacement_carrier_authority": False,
            })
            result = root / "jobs/protein-active-learning-trial-0/trial/result.json"
            write_json(result, {"verifier_result": {"rewards": {"reward": 1.0}}})
            env = {
                "GITHUB_WORKSPACE": str(root),
                "SAFE_ID": "protein-active-learning-trial-0",
                "CACHE_READY": "true",
                "HARBOR_OUTCOME": "success",
            }
            expected_material = {
                "epoch_git_blob_sha": epoch_blob,
                "execution_claim_git_blob_sha": claim_blob,
                "bound": True,
            }
            with patch.dict(os.environ, env, clear=False), patch.object(
                finalizer.start_cas,
                "_runtime_identity",
                return_value=("e" * 64, expected_material),
            ):
                self.assertEqual(finalizer.main(), 0)
            receipt = json.loads(
                (root / "protein-active-learning-trial-0__SLOT_RECEIPT_V4.json").read_text()
            )
        self.assertEqual(receipt["status"], "FINAL_ZERO")
        self.assertIn("START_CAS_IDENTITY_INVALID:RUNTIME_IDENTITY_RECOMPUTED_MATCH", receipt["errors"])
        self.assertIn("START_CAS_IDENTITY_INVALID:RUNTIME_IDENTITY_MATERIAL_EXACT_MATCH", receipt["errors"])
        self.assertIn("START_CAS_IDENTITY_INVALID:WORKFLOW_CAS_MATCH", receipt["errors"])
        self.assertIn("START_CAS_IDENTITY_INVALID:AUTHORITY_CAS_MATCH", receipt["errors"])
        self.assertIn("START_CAS_IDENTITY_INVALID:ACTIVATION_CAS_MATCH", receipt["errors"])

    def test_finalizer_accepts_exact_recomputed_current_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "RANK15_PRESTART_GUARD.json"
            write_json(guard, {
                "pass": True,
                "task_read": True,
                "task_started": False,
                "logical_attempt_id": "a" * 64,
            })
            workflow = root / "workflow.yml"
            workflow.write_text("workflow-v4\n", encoding="utf-8")
            authority = root / "authority.json"
            write_json(authority, {"authority": "current"})
            activation = root / "activate.json"
            write_json(activation, {"activate": True})
            epoch = root / "epoch.json"
            epoch_blob = write_json(epoch, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EPOCH_V4"})
            claim = root / "claim.json"
            claim_blob = write_json(claim, {"schema": "PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_CLAIM_V4"})
            workflow_blob = git_blob(workflow)
            authority_blob = git_blob(authority)
            activation_blob = git_blob(activation)
            write_json(root / "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json", {
                "workflow_path": "workflow.yml",
                "workflow_git_blob_sha": workflow_blob,
                "authority": {"path": "authority.json", "git_blob_sha": authority_blob},
                "activation_path": "activate.json",
                "epoch": {"path": "epoch.json", "git_blob_sha": epoch_blob},
                "execution_claim": {"path": "claim.json", "git_blob_sha": claim_blob},
            })
            expected_material = {
                "epoch_git_blob_sha": epoch_blob,
                "execution_claim_git_blob_sha": claim_blob,
                "bound": True,
            }
            runtime_sha = "e" * 64
            write_json(root / "RANK15_START_CAS_V4.json", {
                "pass": True,
                "acquired": True,
                "task_started": True,
                "slot_id": finalizer.SLOT,
                "task_digest": finalizer.DIGEST,
                "generic_cas_key": finalizer._slot_start_key(),
                "logical_attempt_id": "a" * 64,
                "runtime_identity_sha256": runtime_sha,
                "runtime_identity_material": expected_material,
                "prestart_receipt_sha256": hashlib.sha256(guard.read_bytes()).hexdigest(),
                "durable_record_sha256": "1" * 64,
                "workflow_git_blob_sha": workflow_blob,
                "authority_git_blob_sha": authority_blob,
                "activation_git_blob_sha": activation_blob,
                "replay_authority": False,
                "replacement_carrier_authority": False,
            })
            result = root / "jobs/protein-active-learning-trial-0/trial/result.json"
            write_json(result, {"verifier_result": {"rewards": {"reward": 1.0}}})
            env = {
                "GITHUB_WORKSPACE": str(root),
                "SAFE_ID": "protein-active-learning-trial-0",
                "CACHE_READY": "true",
                "HARBOR_OUTCOME": "success",
            }
            with patch.dict(os.environ, env, clear=False), patch.object(
                finalizer.start_cas,
                "_runtime_identity",
                return_value=(runtime_sha, expected_material),
            ):
                self.assertEqual(finalizer.main(), 0)
            receipt = json.loads(
                (root / "protein-active-learning-trial-0__SLOT_RECEIPT_V4.json").read_text()
            )
        self.assertEqual(receipt["status"], "SUCCESS")
        self.assertTrue(receipt["start_cas_identity_valid"])
        self.assertEqual(receipt["errors"], [])



if __name__ == "__main__":
    unittest.main(verbosity=2)
