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

def promoted_route():
    cfg = load_config()
    route = copy.deepcopy(cfg["source_gate_v2_candidate"])
    materiality = evaluate_materiality_counterfactual()
    route["general_substrate_test_pass"] = bool(materiality["pass"])
    route["configuration_materially_constrains_execution"] = bool(
        materiality["configuration_material_control_proven"]
    )
    return route

class Tests(unittest.TestCase):
    def test_exact_candidate_starts_fail_closed(self):
        cfg = load_config()
        self.assertFalse(cfg["source_gate_v2_candidate"]["general_substrate_test_pass"])
        self.assertFalse(cfg["clean_direct_case_execution_authority"])
        out = evaluate(cfg["source_gate_v2_candidate"])
        self.assertFalse(out["pass"], out)
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN", out["errors"])

    def test_materiality_precondition_is_true(self):
        out = evaluate_materiality_counterfactual()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["configuration_material_control_proven"])
        self.assertFalse(out["benchmark_case_content_consumed"])
        self.assertFalse(out["hidden_oracle_case_content_consumed"])

    def test_promoted_finance_route_passes_source_gate_v2(self):
        out = evaluate(promoted_route())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["clean_case_execution_authority"])

    def test_promoted_unknown_domain_route_passes_same_source_gate_v2(self):
        out = evaluate(promoted_route())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["clean_case_execution_authority"])

    def test_materiality_removal_fails_closed(self):
        route = promoted_route()
        route["configuration_materially_constrains_execution"] = False
        route["general_substrate_test_pass"] = False
        out = evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN", out["errors"])
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
