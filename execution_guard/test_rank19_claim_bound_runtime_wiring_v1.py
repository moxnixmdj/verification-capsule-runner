from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRESTART = ROOT / "capsules/tb_science_rank19_20261010_v1/rank19_prestart_token_guard_v4.py"
START = ROOT / "capsules/tb_science_rank19_20261010_v1/rank19_start_cas_v6.py"
RUNNER = ROOT / "capsules/tb_science_rank19_20261010_v1/rank19_v6_status_journal_runner.py"
BEHAVIOR = ROOT / "execution_guard/TB_SCIENCE_RANK19_EXECUTION_BEHAVIOR_V1.json"


class Rank19ClaimBoundRuntimeWiringTests(unittest.TestCase):
    def test_prestart_resolves_claim_identity_before_task_download(self):
        text = PRESTART.read_text(encoding="utf-8")
        self.assertNotIn("logical_attempt_identity_v1", text)
        self.assertIn("resolve_claim_bound_identity", text)
        self.assertIn("execution_claim_binding_digest", text)
        self.assertLess(
            text.index("resolve_claim_bound_identity("),
            text.index('"harbor", "task", "download"'),
        )

    def test_status_runner_validates_carried_claim_bound_identity(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("logical_attempt_identity_v1", text)
        self.assertIn("resolve_claim_bound_identity", text)
        self.assertIn("LOGICAL_ATTEMPT_ID_NOT_CLAIM_BOUND", text)

    def test_start_cas_validates_guard_against_bound_claim_identity(self):
        text = START.read_text(encoding="utf-8")
        self.assertNotIn("logical_attempt_identity_v1", text)
        self.assertIn("resolve_claim_bound_identity", text)
        self.assertIn("PRESTART_LOGICAL_ATTEMPT_ID_NOT_CLAIM_BOUND", text)

    def test_behavior_binds_v2_identity_and_claim_resolver(self):
        behavior = json.loads(BEHAVIOR.read_text(encoding="utf-8"))
        facts = behavior["behavior"]
        bindings = behavior["runtime_bindings"]
        self.assertTrue(facts["execution_claim_bound_logical_attempt_identity"])
        self.assertEqual(
            bindings["identity_primitive"]["path"],
            "execution_guard/logical_attempt_identity_v2.py",
        )
        self.assertEqual(
            bindings["identity_primitive"]["git_blob_sha"],
            "6329aff3f22ddbb6fdd21c6ada0a3b08c6f569c7",
        )
        self.assertEqual(
            bindings["claim_bound_identity_resolver"]["path"],
            "execution_guard/rank19_claim_bound_identity_v1.py",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
