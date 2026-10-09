from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_guard import terminal_causal_journal_filebridge_v1 as bridge
from execution_guard import terminal_causal_journal_v1 as journal


class MemoryStore:
    def __init__(self):
        self.rows = {}

    def create(self, key, value):
        if key in self.rows:
            return False
        self.rows[key] = json.loads(json.dumps(value))
        return True

    def read(self, key):
        value = self.rows.get(key)
        return None if value is None else json.loads(json.dumps(value))


class TerminalCausalJournalFileBridgeTests(unittest.TestCase):
    def setUp(self):
        self.logical = "a" * 64

    def _event(self, *, action_id="A1"):
        return journal.make_event(
            logical_attempt_id=self.logical,
            sequence=0,
            predecessor_sha256=None,
            kind="PLANNER_PROPOSAL_ACTION_INTENT",
            payload={
                "cycle": 0,
                "action_id": action_id,
                "command_sha256": "b" * 64,
            },
        )

    def test_request_requires_parent_commit_before_ack_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            event = self._event()
            request_path, ack_path = bridge.publish_request(root, event)
            self.assertTrue(request_path.is_file())
            self.assertFalse(ack_path.exists())

            store = MemoryStore()
            ack = bridge.process_request(store, request_path)
            self.assertTrue(ack_path.is_file())
            self.assertEqual(ack["event_sha256"], event["event_sha256"])
            waited = bridge.wait_for_ack(root, event, timeout_s=0.2, poll_s=0.01)
            self.assertEqual(waited["event_sha256"], event["event_sha256"])

    def test_exact_request_publish_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            event = self._event()
            first = bridge.publish_request(root, event)
            second = bridge.publish_request(root, event)
            self.assertEqual(first, second)

    def test_parent_rejects_tampered_request_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            event = self._event()
            request_path, _ack = bridge.publish_request(root, event)
            value = json.loads(request_path.read_text())
            value["event"]["payload"]["action_id"] = "tampered"
            request_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(journal.JournalError, "PAYLOAD_SHA256_MISMATCH"):
                bridge.process_request(MemoryStore(), request_path)

    def test_conflicting_same_sequence_never_gets_second_ack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore()
            first = self._event(action_id="A1")
            second = self._event(action_id="A2")
            first_req, first_ack = bridge.publish_request(root, first)
            second_req, second_ack = bridge.publish_request(root, second)

            bridge.process_request(store, first_req)
            self.assertTrue(first_ack.is_file())
            with self.assertRaisesRegex(journal.JournalError, "JOURNAL_FORK_REJECTED"):
                bridge.process_request(store, second_req)
            self.assertFalse(second_ack.exists())

    def test_process_pending_commits_each_unacked_request_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore()
            e0 = self._event()
            bridge.publish_request(root, e0)
            self.assertEqual(bridge.process_pending_once(store, root), 1)
            self.assertEqual(bridge.process_pending_once(store, root), 0)

            prefix = journal.recover_prefix(store, self.logical)
            e1 = journal.next_event(
                prefix,
                logical_attempt_id=self.logical,
                kind="ACTION_VERIFY_STATE_COMMIT",
                payload={"action_id": "A1", "returncode": 0},
            )
            bridge.publish_request(root, e1)
            self.assertEqual(bridge.process_pending_once(store, root), 1)
            recovered = journal.recover_prefix(store, self.logical)
            self.assertEqual([x["sequence"] for x in recovered], [0, 1])

    def test_wait_without_parent_ack_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            event = self._event()
            bridge.publish_request(root, event)
            with self.assertRaisesRegex(bridge.JournalFileBridgeError, "ACK_TIMEOUT"):
                bridge.wait_for_ack(root, event, timeout_s=0.03, poll_s=0.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)
