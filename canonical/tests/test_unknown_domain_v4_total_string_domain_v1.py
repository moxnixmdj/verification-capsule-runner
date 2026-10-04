from __future__ import annotations

import unittest

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


class TotalStringDomainRepairTests(unittest.TestCase):
    def test_v3_claimed_string_domain_has_reachable_unicode_counterexample(self):
        beacon="A"*16+"\ud800"
        with self.assertRaises(UnicodeEncodeError):
            g3._generate(
                beacon=beacon,
                evaluator_secret=b"S"*32,
                namespace="V3-UNICODE-FALSIFIER",
            )

    def test_v4_totalizes_surrogate_beacon_and_secret_without_production(self):
        beacons=[
            "A"*16+"\ud800",
            "\udfff"+"B"*16,
            "Ω"*16,
            "\x00"+"C"*16,
        ]
        secrets=[
            b"S"*32,
            "T"*31+"\ud800",
            "\udfff"+"U"*31,
            "λ"*32,
        ]
        for i,beacon in enumerate(beacons):
            for j,secret in enumerate(secrets):
                packet=g4._generate(
                    beacon=beacon,
                    evaluator_secret=secret,
                    namespace=f"V4-UNICODE-{i}-{j}",
                )
                self.assertEqual(packet["case_count"],27)
                self.assertEqual(len(packet["visible_cases"]),27)
                self.assertEqual(len(packet["hidden_records"]),27)
                rows=[]
                for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
                    out=harness.execute_case(
                        candidate_step=candidate.step,
                        case_visible=visible,
                        hidden_record=hidden,
                    )
                    self.assertTrue(out["scorer_result"]["pass"],out["scorer_result"])
                    rows.append(out["scorer_result"])
                self.assertTrue(scorer.aggregate(rows)["all_27_cases_pass"])
                self.assertEqual(packet["string_domain_totality"],g4.STRING_DOMAIN_TOTALITY)

    def test_beacon_canonicalization_is_injective_on_known_utf8_surrogate_boundary_cases(self):
        values=[
            "A"*16,
            "A"*16+"\ud800",
            "A"*16+"\ud801",
            "A"*16+"�",
            "A"*16+"😀",
            "\udfff"+"A"*16,
        ]
        encoded=[g4._canonical_beacon(x) for x in values]
        self.assertEqual(len(encoded),len(set(encoded)))
        self.assertTrue(all(x.isascii() for x in encoded))


if __name__=="__main__":
    unittest.main(verbosity=2)
