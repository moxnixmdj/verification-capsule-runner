import copy
import json
import pathlib
import unittest

from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate
from canonical.runtime.judgment_control_envelope_v1 import evaluate_materiality_counterfactual

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = ROOT / "canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json"

def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def materiality_only_route():
    cfg = load_config()
    route = copy.deepcopy(cfg["source_gate_v2_candidate"])
    materiality = evaluate_materiality_counterfactual()
    route["configuration_materially_constrains_execution"] = bool(
        materiality["configuration_material_control_proven"]
    )
    return route

class Tests(unittest.TestCase):
    def test_exact_candidate_starts_fail_closed(self):
        cfg = load_config()
        route = cfg["source_gate_v2_candidate"]
        self.assertFalse(route["general_substrate_test_pass"])
        self.assertFalse(route["configuration_materially_constrains_execution"])
        self.assertFalse(cfg["clean_direct_case_execution_authority"])
        out = evaluate(route)
        self.assertFalse(out["pass"], out)
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN", out["errors"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN", out["errors"])

    def test_materiality_counterfactual_is_zero_case_and_passes(self):
        out = evaluate_materiality_counterfactual()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["configuration_material_control_proven"])
        self.assertFalse(out["benchmark_case_content_consumed"])
        self.assertFalse(out["hidden_oracle_case_content_consumed"])
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_materiality_only_does_not_launder_general_substrate_qualification(self):
        route = materiality_only_route()
        self.assertTrue(route["configuration_materially_constrains_execution"])
        self.assertFalse(route["general_substrate_test_pass"])
        out = evaluate(route)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["errors"], ["GENERAL_SUBSTRATE_TEST_NOT_PROVEN"])
        self.assertFalse(out["clean_case_execution_authority"])

    def test_hypothetical_separate_substrate_receipt_would_complete_gate(self):
        route = materiality_only_route()
        route["general_substrate_test_pass"] = True
        out = evaluate(route)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["clean_case_execution_authority"])

    def test_materiality_removal_fails_closed_even_with_hypothetical_substrate_receipt(self):
        route = materiality_only_route()
        route["general_substrate_test_pass"] = True
        route["configuration_materially_constrains_execution"] = False
        out = evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
