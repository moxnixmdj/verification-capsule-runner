from __future__ import annotations

import json
import unittest

from execution_guard import terminal_causal_journal_v1 as journal


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.create_error_after_write = False
        self.create_error_before_write = False
        self.read_error = False

    def create(self, key, value):
        if self.create_error_before_write:
            raise RuntimeError("create failed before write")
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


class TerminalCausalJournalTests(unittest.TestCase):
    def setUp(self):
        self.logical = "a" * 64

    def _event0(self, payload=None):
        return journal.make_event(
            logical_attempt_id=self.logical,
            sequence=0,
            predecessor_sha256=None,
            kind="PLANNER_PROPOSAL_ACTION_INTENT",
            payload=payload or {
                "cycle": 0,
                "proposal_sha256": "b" * 64,
                "action_id": "A1",
                "command_sha256": "c" * 64,
            },
        )

    def test_append_and_recover_exact_chain(self):
        store = MemoryStore()
        e0 = self._event0()
        r0 = journal.append_once(store, e0)
        self.assertEqual(r0["status"], "COMMITTED")

        prefix = journal.recover_prefix(store, self.logical)
        e1 = journal.next_event(
            prefix,
            logical_attempt_id=self.logical,
            kind="ACTION_VERIFY_STATE_COMMIT",
            payload={
                "action_id": "A1",
                "returncode": 0,
                "stdout_sha256": "d" * 64,
                "stderr_sha256": "e" * 64,
                "verification_returncode": 0,
                "resolved_requirement_ids": ["R1"],
            },
        )
        journal.append_once(store, e1)

        recovered = journal.recover_prefix(store, self.logical)
        self.assertEqual([x["sequence"] for x in recovered], [0, 1])
        self.assertEqual(recovered[1]["predecessor_sha256"], recovered[0]["event_sha256"])

    def test_exact_duplicate_is_idempotent(self):
        store = MemoryStore()
        e0 = self._event0()
        journal.append_once(store, e0)
        result = journal.append_once(store, e0)
        self.assertEqual(result["status"], "COMMITTED_IDEMPOTENT")

    def test_conflicting_same_sequence_is_rejected_as_fork(self):
        store = MemoryStore()
        e0 = self._event0()
        journal.append_once(store, e0)
        conflict = self._event0({
            "cycle": 0,
            "proposal_sha256": "f" * 64,
            "action_id": "OTHER",
            "command_sha256": "0" * 64,
        })
        with self.assertRaisesRegex(journal.JournalError, "JOURNAL_FORK_REJECTED"):
            journal.append_once(store, conflict)

    def test_lost_create_response_reconciles_exact_persisted_event(self):
        store = MemoryStore()
        store.create_error_after_write = True
        e0 = self._event0()
        result = journal.append_once(store, e0)
        self.assertEqual(
            result["status"],
            "COMMITTED_RECONCILED_AFTER_CREATE_ERROR",
        )
        recovered = journal.recover_prefix(store, self.logical)
        self.assertEqual(recovered[0]["event_sha256"], e0["event_sha256"])

    def test_create_error_with_confirmed_absence_is_not_committed(self):
        store = MemoryStore()
        store.create_error_before_write = True
        with self.assertRaisesRegex(
            journal.JournalError,
            "APPEND_NOT_PRESENT_AFTER_CREATE_ERROR",
        ):
            journal.append_once(store, self._event0())
        self.assertEqual(journal.recover_prefix(store, self.logical), [])

    def test_create_and_read_uncertainty_is_explicit(self):
        store = MemoryStore()
        store.create_error_before_write = True
        store.read_error = True
        with self.assertRaisesRegex(journal.JournalError, "APPEND_OUTCOME_UNCONFIRMED"):
            journal.append_once(store, self._event0())

    def test_recovery_rejects_broken_predecessor_chain(self):
        store = MemoryStore()
        e0 = self._event0()
        store.rows[journal.event_key(self.logical, 0)] = e0
        e1 = journal.make_event(
            logical_attempt_id=self.logical,
            sequence=1,
            predecessor_sha256="f" * 64,
            kind="PLANNER_NO_ACTION",
            payload={"cycle": 1, "reason": "none"},
        )
        store.rows[journal.event_key(self.logical, 1)] = e1
        with self.assertRaisesRegex(journal.JournalError, "RECOVERY_CHAIN_MISMATCH:1"):
            journal.recover_prefix(store, self.logical)

    def test_secret_bearing_payload_keys_are_rejected(self):
        for payload in (
            {"token": "x"},
            {"nested": {"api_key": "x"}},
            {"password": "x"},
            {"github_token": "x"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(
                    journal.JournalError,
                    "SECRET_BEARING_KEY_REJECTED",
                ):
                    self._event0(payload)

    def test_token_count_metadata_is_not_mistaken_for_secret(self):
        event = self._event0({
            "input_tokens": 1234,
            "reserved_completion_tokens": 4096,
        })
        self.assertEqual(event["payload"]["input_tokens"], 1234)

    def test_tampered_payload_hash_is_rejected(self):
        event = self._event0()
        event["payload"]["action_id"] = "tampered"
        with self.assertRaisesRegex(journal.JournalError, "PAYLOAD_SHA256_MISMATCH"):
            journal.validate_event(event)


if __name__ == "__main__":
    unittest.main(verbosity=2)
