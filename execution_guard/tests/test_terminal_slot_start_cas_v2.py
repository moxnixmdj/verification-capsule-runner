from __future__ import annotations

import json
import unittest

from execution_guard import terminal_slot_start_cas_v2 as v2

v1 = v2.v1


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.raise_create = False
        self.raise_read = False

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
        return None if value is None else json.loads(json.dumps(value))


def intent_v2() -> v2.StartIntent:
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


def intent_v1() -> v1.StartIntent:
    i = intent_v2()
    return v1.StartIntent(
        slot_id=i.slot_id,
        task_digest=i.task_digest,
        logical_attempt_id=i.logical_attempt_id,
        workflow_git_blob_sha=i.workflow_git_blob_sha,
        authority_git_blob_sha=i.authority_git_blob_sha,
        activation_git_blob_sha=i.activation_git_blob_sha,
        runtime_identity_sha256=i.runtime_identity_sha256,
        prestart_receipt_sha256=i.prestart_receipt_sha256,
        github_run_id=i.github_run_id,
        github_sha=i.github_sha,
    )


class TerminalSlotStartCASV2Tests(unittest.TestCase):
    def test_v2_reuses_v1_namespace_and_exact_slot_key(self):
        i = intent_v2()
        self.assertEqual(v2.NAMESPACE, v1.NAMESPACE)
        self.assertEqual(
            v2.slot_start_key(i.slot_id, i.task_digest),
            v1.slot_start_key(i.slot_id, i.task_digest),
        )

    def test_v2_commit_binds_agent_ready_receipt_and_consumption_boundary(self):
        store = MemoryStore()
        i = intent_v2()
        receipt = v2.reserve_start_once(store, i)
        record = store.read(v2.slot_start_key(i.slot_id, i.task_digest))
        self.assertEqual(receipt["status"], "AGENT_READY_BOUND_START_COMMITTED")
        self.assertTrue(receipt["task_started"])
        self.assertEqual(receipt["benchmark_trials_consumed"], 1)
        self.assertEqual(record["agent_ready_receipt_sha256"], i.agent_ready_receipt_sha256)
        self.assertTrue(record["task_started"])
        self.assertEqual(record["benchmark_trials_consumed"], 1)
        self.assertFalse(record["replay_authority"])
        self.assertFalse(record["replacement_carrier_authority"])

    def test_existing_v1_record_blocks_v2_commit(self):
        store = MemoryStore()
        old = intent_v1()
        v1.reserve_start_once(store, old)
        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_ALREADY_COMMITTED__NO_SECOND_AGENT_RELEASE",
        ):
            v2.reserve_start_once(store, intent_v2())

    def test_existing_v2_record_blocks_v1_commit(self):
        store = MemoryStore()
        new = intent_v2()
        v2.reserve_start_once(store, new)
        with self.assertRaisesRegex(v1.StartAdmissionDenied, "START_ALREADY_RESERVED"):
            v1.reserve_start_once(store, intent_v1())

    def test_unconfirmed_create_never_releases_agent(self):
        store = MemoryStore()
        store.raise_create = True
        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_COMMIT_UNCONFIRMED__NO_AGENT_RELEASE",
        ):
            v2.reserve_start_once(store, intent_v2())

    def test_postwrite_read_failure_never_releases_agent(self):
        class ReadFailsAfterCreate(MemoryStore):
            def create(self, key, value):
                out = super().create(key, value)
                self.raise_read = True
                return out

        with self.assertRaisesRegex(
            v2.StartAdmissionDenied,
            "START_POSTWRITE_READ_UNCONFIRMED__NO_AGENT_RELEASE",
        ):
            v2.reserve_start_once(ReadFailsAfterCreate(), intent_v2())

    def test_ready_hash_is_required(self):
        i = intent_v2()
        broken = v2.StartIntent(
            slot_id=i.slot_id,
            task_digest=i.task_digest,
            logical_attempt_id=i.logical_attempt_id,
            workflow_git_blob_sha=i.workflow_git_blob_sha,
            authority_git_blob_sha=i.authority_git_blob_sha,
            activation_git_blob_sha=i.activation_git_blob_sha,
            runtime_identity_sha256=i.runtime_identity_sha256,
            prestart_receipt_sha256=i.prestart_receipt_sha256,
            agent_ready_receipt_sha256="not-a-hash",
            github_run_id=i.github_run_id,
            github_sha=i.github_sha,
        )
        with self.assertRaisesRegex(ValueError, "INVALID_AGENT_READY_RECEIPT_SHA256"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
