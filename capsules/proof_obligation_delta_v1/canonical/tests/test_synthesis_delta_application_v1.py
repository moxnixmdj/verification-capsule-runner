from __future__ import annotations
import json
from pathlib import Path
import unittest

from canonical.runtime.proof_obligation_delta_compiler_v1 import compile_delta

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_INPUT_V1.json"

class SynthesisDeltaApplicationTests(unittest.TestCase):
    def test_live_synthesis_residual_is_exact_and_fail_closed(self):
        doc=json.loads(INPUT.read_text())
        out=compile_delta(doc)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"RESIDUAL_DELTA_OPEN")
        self.assertIsNone(out["scope_relation"])
        self.assertEqual(out["residual"],doc["expected_residual"])
        self.assertEqual(
            out["covered"]["atoms"],
            sorted([
                "dimension:audience_adaptation",
                "dimension:claim_to_source_fidelity",
                "dimension:compression_without_decision_relevant_loss",
                "dimension:format_and_style_constraints",
                "dimension:required_evidence_coverage",
                "dimension:uncertainty_and_disagreement_preservation",
                "metric:required_claim_coverage",
            ])
        )
        self.assertEqual(out["covered"]["scope_components"],[])
        self.assertEqual(out["covered"]["metrics"],[])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
