import json
import pathlib
import unittest

from canonical.runtime.proof_route_dominance import evaluate


class GlobalSurfaceDominanceV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[2]
        cls.payload = json.loads(
            (root / "canonical/governance/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V3.json").read_text()
        )
        cls.out = evaluate(cls.payload)

    def test_complete_zero_uncovered(self):
        self.assertEqual(self.out["status"], "COMPLETE")
        self.assertEqual(self.out["global_uncovered_obligations"], [])

    def test_every_named_surface_is_redundant_as_execution_route(self):
        surface_ids = {
            row["id"] for row in self.payload["routes"]
            if row["id"].startswith("SURFACE_")
        }
        verdicts = {
            row["route_id"]: row
            for row in self.out["blocked_route_verdicts"]
            if row["route_id"].startswith("SURFACE_")
        }
        self.assertEqual(set(verdicts), surface_ids)
        self.assertGreaterEqual(len(surface_ids), 14)
        for sid in sorted(surface_ids):
            self.assertTrue(verdicts[sid]["redundant"], sid)
            self.assertEqual(verdicts[sid]["uncovered_obligations"], [], sid)

    def test_all_ten_frozen_behavioral_obligations_have_admissible_support(self):
        expected = {row["id"] for row in self.payload["obligations"]}
        self.assertEqual(len(expected), 10)
        self.assertEqual(set(self.out["obligation_support"]), expected)
        for oid in sorted(expected):
            self.assertTrue(self.out["obligation_support"][oid], oid)

    def test_no_benchmark_score_equivalence_claim_is_created(self):
        self.assertEqual(self.payload["capability_credit_delta"], 0)
        self.assertEqual(self.payload["family_credit_delta"], 0)
        self.assertEqual(self.payload["fresh_terminal_evidence_consumed"], 0)
        self.assertEqual(self.payload["incremental_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main()
