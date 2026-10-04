from __future__ import annotations

import unittest

from canonical.runtime import unknown_domain_direct_candidate_v2 as v2
from canonical.runtime import unknown_domain_direct_candidate_v3 as v3
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as gen
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness


class UnknownDomainDirectCandidateV3Tests(unittest.TestCase):
    def _execute(self, candidate, beacon: str, index: int):
        packet = gen.generate_qualification_fixture_population(beacon=beacon)
        return harness.execute_case(
            candidate_step=candidate.step,
            case_visible=packet["visible_cases"][index],
            hidden_record=packet["hidden_records"][index],
        )

    def test_regression_one_ulp_add2_role_swap(self):
        beacon = "FLOAT-ROLE-SWAP-000000000004"
        old = self._execute(v2, beacon, 4)
        self.assertFalse(old["scorer_result"]["pass"], old)
        self.assertIn(
            "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG",
            old["scorer_result"]["errors"],
        )

        fixed = self._execute(v3, beacon, 4)
        self.assertTrue(fixed["scorer_result"]["pass"], fixed)
        self.assertLess(fixed["probe_count"], 3)

    def test_add2_public_role_signatures_are_distinct_and_cross_domain_stable(self):
        packet = gen.generate_qualification_fixture_population(
            beacon="ROLE-SIGNATURE-STRUCTURAL-PROOF-0001"
        )
        for index in (4, 10):
            case = packet["visible_cases"][index]
            rec = case["domain_a"]["earned_receipts"][0]
            program = rec["normalized_primitive_program"]
            self.assertEqual(program["op"], "ADD2")
            mappings = {
                role: rec["source_role_binding"][role]
                for role in program["roles"]
            }
            src = {
                role: v3._feature_signature(case["domain_a"]["tasks"], fid)
                for role, fid in mappings.items()
            }
            self.assertEqual(src["r0"], (-1, 1, -1))
            self.assertEqual(src["r1"], (1, -1, 1))
            self.assertNotEqual(src["r0"], src["r1"])

            # The true target features are not exposed as role labels, so infer
            # them from a scored V3 trace and verify the public signatures.
            out = self._execute(v3, "ROLE-SIGNATURE-STRUCTURAL-PROOF-0001", index)
            self.assertTrue(out["scorer_result"]["pass"], out)
            action = out["candidate_terminal_action"]
            support = action["support_feature_ids"]
            target_sigs = {
                fid: v3._feature_signature(case["domain_b"]["tasks"], fid)
                for fid in support
            }
            self.assertEqual(set(target_sigs.values()), {src["r0"], src["r1"]})

    def test_v3_passes_broad_zero_production_qualification_grid(self):
        for n in range(32):
            beacon = f"V3-QUAL-GRID-{n:012d}"
            packet = gen.generate_qualification_fixture_population(beacon=beacon)
            self.assertFalse(packet["production"])
            self.assertEqual(packet["case_count"], 27)
            for case, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
                out = harness.execute_case(
                    candidate_step=v3.step,
                    case_visible=case,
                    hidden_record=hidden,
                )
                self.assertTrue(
                    out["scorer_result"]["pass"],
                    (beacon, case["case_id"], out),
                )
                self.assertLess(out["probe_count"], 3)
                action = out["candidate_terminal_action"]
                self.assertEqual(action.get("persistent_learned_bytes", 0), 0)
                self.assertEqual(action.get("external_frontier_model_calls", 0), 0)
                self.assertEqual(action.get("external_learned_capability_calls", 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
