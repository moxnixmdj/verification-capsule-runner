from __future__ import annotations

import json
import unittest

from execution_guard import terminal_slot_start_cas_v2 as v2


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.create_error_before_write = False
        self.create_error_after_write = False
        self.read_error = False

    def create(self, key, value):
        if self.create_error_before_write:
            raise RuntimeError("create before write")
        if key in self.rows:
            return False
        self.rows[key] = json.loads(json.dumps(value))
        if self.create_error_after_write:
            raise RuntimeError("response lost after write")
        return True

    def read(self, key):
        if self.read_error:
            raise RuntimeError("read unavailable")
        value = self.rows.get(key)
        return None if value is None else json.loads(json.dumps(value))


def intent() -> v2.StartIntent:
    return v2.StartIntent(
        slot_id="terminal-bench-science/example::trial-0",
        task_digest="sha256:" + "1" * 64,
        logical_attempt_id="2" * 64,
        workflow_git_blob_sha="3" * 40,
        authority_git_blob_sha="4" * 40,
        activation_git_blob_sha="5" * 40,
        runtime_identity_sha256="6" * 64,
        prestart_receipt_sha256="7" * 64,
        agent_ready_receipt_sha256="8" * 64,
        github_run_id="123",
        github_sha="9" * 40,
    )


class TerminalSlotStartStatusBackendTests(unittest.TestCase):
    def test_create_error_with_confirmed_absence_is_nonconsuming(self):
        store = MemoryStore()
        store.create_error_before_write = True
        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_COMMIT_CONFIRMED_ABSENT__NO_AGENT_RELEASE",
        ):
            v2.reserve_start_once(store, intent())
        self.assertEqual(store.rows, {})

    def test_lost_create_response_reconciles_exact_persisted_start(self):
        store = MemoryStore()
        store.create_error_after_write = True
        receipt = v2.reserve_start_once(store, intent())
        self.assertEqual(
            receipt["status"],
            "AGENT_READY_BOUND_START_COMMITTED_RECONCILED_AFTER_CREATE_ERROR",
        )
        self.assertTrue(receipt["task_started"])
        self.assertEqual(receipt["benchmark_trials_consumed"], 1)

    def test_exact_duplicate_is_same_committed_start(self):
        store = MemoryStore()
        i = intent()
        first = v2.reserve_start_once(store, i)
        second = v2.reserve_start_once(store, i)
        self.assertEqual(first["logical_attempt_id"], second["logical_attempt_id"])
        self.assertEqual(
            second["status"],
            "AGENT_READY_BOUND_START_COMMITTED_IDEMPOTENT",
        )
        self.assertEqual(len(store.rows), 1)

    def test_conflicting_same_slot_never_releases_second_agent(self):
        store = MemoryStore()
        v2.reserve_start_once(store, intent())
        i = intent()
        other = v2.StartIntent(
            slot_id=i.slot_id,
            task_digest=i.task_digest,
            logical_attempt_id="a" * 64,
            workflow_git_blob_sha=i.workflow_git_blob_sha,
            authority_git_blob_sha=i.authority_git_blob_sha,
            activation_git_blob_sha=i.activation_git_blob_sha,
            runtime_identity_sha256=i.runtime_identity_sha256,
            prestart_receipt_sha256=i.prestart_receipt_sha256,
            agent_ready_receipt_sha256=i.agent_ready_receipt_sha256,
            github_run_id="456",
            github_sha=i.github_sha,
        )
        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_ALREADY_COMMITTED__NO_SECOND_AGENT_RELEASE",
        ):
            v2.reserve_start_once(store, other)

    def test_create_and_read_uncertainty_never_releases(self):
        store = MemoryStore()
        store.create_error_before_write = True
        store.read_error = True
        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_COMMIT_OUTCOME_UNCONFIRMED__NO_AGENT_RELEASE",
        ):
            v2.reserve_start_once(store, intent())


if __name__ == "__main__":
    unittest.main(verbosity=2)
