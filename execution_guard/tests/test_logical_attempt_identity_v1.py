from __future__ import annotations

import unittest

from execution_guard.logical_attempt_identity_v1 import (
    LogicalAttemptIdentityError,
    logical_attempt_id,
    logical_attempt_identity,
)


D1 = "sha256:" + "a" * 64
D2 = "sha256:" + "b" * 64


class LogicalAttemptIdentityV1Tests(unittest.TestCase):
    def test_same_slot_and_digest_are_stable(self):
        left = logical_attempt_id(slot_id="family/task::trial-0", task_digest=D1)
        right = logical_attempt_id(slot_id="family/task::trial-0", task_digest=D1)
        self.assertEqual(left, right)
        self.assertEqual(len(left), 64)

    def test_different_slots_do_not_collide_when_task_digest_matches(self):
        a = logical_attempt_id(slot_id="family/a::trial-0", task_digest=D1)
        b = logical_attempt_id(slot_id="family/b::trial-0", task_digest=D1)
        self.assertNotEqual(a, b)

    def test_different_task_digests_do_not_collide_when_slot_matches(self):
        a = logical_attempt_id(slot_id="family/task::trial-0", task_digest=D1)
        b = logical_attempt_id(slot_id="family/task::trial-0", task_digest=D2)
        self.assertNotEqual(a, b)

    def test_carrier_identity_is_deliberately_not_an_input(self):
        base = logical_attempt_identity(
            slot_id="terminal-bench-science/protein-active-learning::trial-0",
            task_digest=D1,
        )
        self.assertEqual(
            set(base),
            {"schema", "slot_id", "task_digest", "logical_attempt_id"},
        )
        self.assertNotIn("github_run_id", base)
        self.assertNotIn("pid", base)
        self.assertNotIn("runner", base)
        self.assertNotIn("workflow_blob", base)
        self.assertNotIn("execution_claim_blob", base)

    def test_whitespace_around_identifiers_is_not_identity(self):
        a = logical_attempt_id(slot_id=" slot-x ", task_digest=" " + D1 + " ")
        b = logical_attempt_id(slot_id="slot-x", task_digest=D1)
        self.assertEqual(a, b)

    def test_invalid_task_digest_fails_closed(self):
        for bad in ("", "sha256:abc", "md5:" + "a" * 32, "sha256:" + "A" * 64):
            with self.assertRaises(LogicalAttemptIdentityError):
                logical_attempt_id(slot_id="slot-x", task_digest=bad)

    def test_empty_or_unbounded_slot_fails_closed(self):
        with self.assertRaises(LogicalAttemptIdentityError):
            logical_attempt_id(slot_id="", task_digest=D1)
        with self.assertRaises(LogicalAttemptIdentityError):
            logical_attempt_id(slot_id="x" * 4097, task_digest=D1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
