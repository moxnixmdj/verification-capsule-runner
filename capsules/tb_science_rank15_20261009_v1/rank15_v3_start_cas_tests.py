from __future__ import annotations

import hashlib
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


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.raise_create = False
        self.raise_read = False
        self.corrupt_after_create = False

    def create(self, key, value):
        if self.raise_create:
            raise RuntimeError("create transport")
        if key in self.rows:
            return False
        self.rows[key] = json.loads(json.dumps(value))
        return True

    def read(self, key):
        if self.raise_read:
            raise RuntimeError("read transport")
        value = self.rows.get(key)
        if value is None:
            return None
        out = json.loads(json.dumps(value))
        if self.corrupt_after_create:
            out["runtime_identity_sha256"] = "0" * 64
        return out


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

        workflow = root / ".github/workflows/execute-tb-science-rank15-20261009-v3.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text("synthetic exact workflow\n", encoding="utf-8")
        authority = root / "authority.json"
        authority.write_text("{}\n", encoding="utf-8")

        surface = root / cas.SURFACE_REL
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text(json.dumps({
            "execution_authority": True,
            "task_started": False,
            "slot_id": cas.SLOT_ID,
            "task_digest": cas.TASK_DIGEST,
            "workflow_path": str(workflow.relative_to(root)),
            "workflow_git_blob_sha": git_blob(workflow),
            "authority": {
                "path": str(authority.relative_to(root)),
                "git_blob_sha": git_blob(authority),
            },
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
            "GITHUB_RUN_ID": "100",
            "GH_TOKEN": "synthetic",
        }

    def _prestart(self, root: Path, logical: str = "a" * 64) -> None:
        (root / cas.PREFLIGHT_RECEIPT).write_text(json.dumps({
            "pass": True,
            "status": "PASS__RANK15_V3_EXACT_TASK_READ__MAXIMAL_RESERVED_CYCLE0_CORE_FITS__TASK_NOT_STARTED",
            "task_read": True,
            "task_started": False,
            "task_digest": cas.TASK_DIGEST,
            "logical_attempt_id": logical,
            "payload_sha256": "b" * 64,
            "request_identity_sha256": "c" * 64,
            "input_tokens": 7000,
        }), encoding="utf-8")

    def _run(self, root: Path, env: dict[str, str], store: MemoryStore, arg: str) -> tuple[int, dict]:
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(cas, "_open_store", return_value=store),
            patch.object(
                cas,
                "_runtime_identity",
                return_value=("d" * 64, {"schema": "SYNTHETIC_RUNTIME_IDENTITY"}),
            ),
            patch.object(sys, "argv", ["cas", arg]),
        ):
            rc = cas.main()
        name = cas.CHECK_RECEIPT if arg == "--check-absent" else cas.ACQUIRE_RECEIPT
        return rc, json.loads((root / name).read_text())

    def test_pre_task_read_check_uses_global_generic_slot_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            store = MemoryStore()
            rc, out = self._run(root, env, store, "--check-absent")
            self.assertEqual(rc, 0)
            self.assertTrue(out["lock_absent"])
            self.assertFalse(out["acquired"])
            self.assertEqual(out["generic_cas_namespace"], cas.generic_cas.NAMESPACE)
            self.assertEqual(
                out["generic_cas_key"],
                cas.generic_cas.slot_start_key(cas.SLOT_ID, cas.TASK_DIGEST),
            )
            self.assertEqual(out["benchmark_trials_consumed"], 0)

    def test_acquire_persists_exact_dynamic_start_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            self._prestart(root)
            store = MemoryStore()
            rc, out = self._run(root, env, store, "--acquire")
            self.assertEqual(rc, 0)
            self.assertTrue(out["acquired"])
            self.assertTrue(out["task_started"])
            self.assertEqual(out["benchmark_trials_consumed"], 1)
            self.assertEqual(out["logical_attempt_id"], "a" * 64)
            self.assertEqual(out["runtime_identity_sha256"], "d" * 64)
            self.assertEqual(out["prestart_payload_sha256"], "b" * 64)
            self.assertEqual(out["prestart_request_identity_sha256"], "c" * 64)

            row = store.rows[out["generic_cas_key"]]
            self.assertEqual(row["logical_attempt_id"], "a" * 64)
            self.assertEqual(row["runtime_identity_sha256"], "d" * 64)
            self.assertEqual(
                row["prestart_receipt_sha256"],
                hashlib.sha256((root / cas.PREFLIGHT_RECEIPT).read_bytes()).hexdigest(),
            )
            self.assertEqual(row["workflow_git_blob_sha"], out["workflow_git_blob_sha"])
            self.assertEqual(row["authority_git_blob_sha"], out["authority_git_blob_sha"])
            self.assertEqual(row["activation_git_blob_sha"], out["activation_git_blob_sha"])
            self.assertFalse(row["replay_authority"])
            self.assertFalse(row["replacement_carrier_authority"])

    def test_second_run_same_slot_is_rejected_by_same_global_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            self._prestart(root)
            store = MemoryStore()
            rc1, _ = self._run(root, env, store, "--acquire")
            self.assertEqual(rc1, 0)
            env2 = dict(env)
            env2["GITHUB_RUN_ID"] = "101"
            rc2, out2 = self._run(root, env2, store, "--acquire")
            self.assertEqual(rc2, 1)
            self.assertFalse(out2["acquired"])
            self.assertFalse(out2["task_started"])
            self.assertEqual(out2["benchmark_trials_consumed"], 0)
            self.assertIn("START_CAS_ALREADY_EXISTS", out2["status"])

    def test_postwrite_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            self._prestart(root)
            store = MemoryStore()
            store.corrupt_after_create = True
            rc, out = self._run(root, env, store, "--acquire")
            self.assertEqual(rc, 1)
            self.assertFalse(out["acquired"])
            self.assertFalse(out["task_started"])
            self.assertIn("POSTWRITE_BINDING_MISMATCH", out["error"])

    def test_store_create_uncertainty_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            self._prestart(root)
            store = MemoryStore()
            store.raise_create = True
            rc, out = self._run(root, env, store, "--acquire")
            self.assertEqual(rc, 1)
            self.assertFalse(out["acquired"])
            self.assertFalse(out["task_started"])
            self.assertEqual(out["benchmark_trials_consumed"], 0)

    def test_invalid_logical_attempt_id_never_reaches_store(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = self._workspace(root)
            self._prestart(root, logical="bad")
            store = MemoryStore()
            rc, out = self._run(root, env, store, "--acquire")
            self.assertEqual(rc, 1)
            self.assertFalse(out["acquired"])
            self.assertEqual(store.rows, {})
            self.assertIn("LOGICAL_ATTEMPT_ID_INVALID", out["error"])

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
            "logical_attempt_id": "a" * 64,
            "payload_sha256": "b" * 64,
            "request_identity_sha256": "c" * 64,
        }), encoding="utf-8")
        prestart_sha = hashlib.sha256((root / "RANK15_PRESTART_GUARD.json").read_bytes()).hexdigest()
        if cas_acquired:
            (root / "RANK15_START_CAS_V3.json").write_text(json.dumps({
                "pass": True,
                "acquired": True,
                "task_started": True,
                "slot_id": finalizer.SLOT,
                "task_digest": finalizer.DIGEST,
                "status": "PASS__DURABLE_BOUND_START_INTENT_COMMITTED__IRREVERSIBLE_SLOT_START",
                "generic_cas_key": finalizer._slot_start_key(),
                "logical_attempt_id": "a" * 64,
                "runtime_identity_sha256": "d" * 64,
                "prestart_receipt_sha256": prestart_sha,
                "durable_record_sha256": "1" * 64,
                "workflow_git_blob_sha": "2" * 40,
                "authority_git_blob_sha": "3" * 40,
                "activation_git_blob_sha": "4" * 40,
                "replay_authority": False,
                "replacement_carrier_authority": False,
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


    def test_cas_identity_mismatch_is_consumed_final_zero_not_retryable(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        guard_path = root / "RANK15_PRESTART_GUARD.json"
        guard_path.write_text(json.dumps({
            "pass": True,
            "task_read": True,
            "task_started": False,
            "logical_attempt_id": "a" * 64,
        }), encoding="utf-8")
        (root / "RANK15_START_CAS_V3.json").write_text(json.dumps({
            "pass": True,
            "acquired": True,
            "task_started": True,
            "slot_id": finalizer.SLOT,
            "task_digest": finalizer.DIGEST,
            "generic_cas_key": finalizer._slot_start_key(),
            "logical_attempt_id": "a" * 64,
            "runtime_identity_sha256": "d" * 64,
            "prestart_receipt_sha256": "0" * 64,
            "durable_record_sha256": "1" * 64,
            "workflow_git_blob_sha": "2" * 40,
            "authority_git_blob_sha": "3" * 40,
            "activation_git_blob_sha": "4" * 40,
            "replay_authority": False,
            "replacement_carrier_authority": False,
        }), encoding="utf-8")
        p = root / "jobs/protein-active-learning-trial-0/trial/result.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"verifier_result":{"rewards":{"reward":1.0}}}), encoding="utf-8")
        env = {
            "GITHUB_WORKSPACE": str(root),
            "SAFE_ID": "protein-active-learning-trial-0",
            "CACHE_READY": "true",
            "HARBOR_OUTCOME": "success",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(finalizer.main(), 0)
        out=json.loads((root/"protein-active-learning-trial-0__SLOT_RECEIPT_V3.json").read_text())
        self.assertEqual(out["status"], "FINAL_ZERO")
        self.assertEqual(out["benchmark_trials_consumed"], 1)
        self.assertEqual(out["consumed_successes_delta"], 0)
        self.assertEqual(out["consumed_final_failures_delta"], 1)
        self.assertFalse(out["start_cas_identity_valid"])
        self.assertFalse(out["rerun_credit"])
        self.assertTrue(any("PRESTART_RECEIPT_SHA_MATCH" in x for x in out["errors"]))

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
