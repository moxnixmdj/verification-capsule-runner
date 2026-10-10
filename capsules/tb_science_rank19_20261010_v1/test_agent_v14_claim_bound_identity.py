from __future__ import annotations

import hashlib
import json
import os
import unittest

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id


SLOT = "synthetic/claim-bound::trial-0"
TASK_DIGEST = "sha256:" + "1" * 64
CLAIM_DIGEST = "sha256:" + "2" * 64


def old_v1_attempt_id() -> str:
    material = json.dumps(
        {
            "schema": "PROJECT_BRAIN_LOGICAL_ATTEMPT_IDENTITY_V1",
            "slot_id": SLOT,
            "task_digest": TASK_DIGEST,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


class AgentV14ClaimBoundIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old = dict(os.environ)
        os.environ["BRAIN_SLOT_ID"] = SLOT
        os.environ["BRAIN_TASK_DIGEST"] = TASK_DIGEST
        os.environ["BRAIN_EXECUTION_CLAIM_BINDING_DIGEST"] = CLAIM_DIGEST

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._old)

    def _agent(self):
        from canonical.runtime import harbor_science_agent_v14 as agent
        return agent

    def test_accepts_exact_v2_claim_bound_attempt(self) -> None:
        expected = logical_attempt_id(
            slot_id=SLOT,
            task_digest=TASK_DIGEST,
            execution_claim_binding_digest=CLAIM_DIGEST,
        )
        os.environ["BRAIN_LOGICAL_ATTEMPT_ID"] = expected
        self.assertEqual(self._agent().logical_attempt_id_for_goal("synthetic goal"), expected)

    def test_rejects_legacy_v1_attempt(self) -> None:
        os.environ["BRAIN_LOGICAL_ATTEMPT_ID"] = old_v1_attempt_id()
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"):
            self._agent().logical_attempt_id_for_goal("synthetic goal")

    def test_requires_claim_binding_digest(self) -> None:
        expected = logical_attempt_id(
            slot_id=SLOT,
            task_digest=TASK_DIGEST,
            execution_claim_binding_digest=CLAIM_DIGEST,
        )
        os.environ["BRAIN_LOGICAL_ATTEMPT_ID"] = expected
        os.environ.pop("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST")
        with self.assertRaisesRegex(RuntimeError, "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED"):
            self._agent().logical_attempt_id_for_goal("synthetic goal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
