import unittest

from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate
from canonical.runtime.judgment_control_envelope_v1 import evaluate_materiality_counterfactual

def route(family):
    materiality = evaluate_materiality_counterfactual()
    return {
        "id": "DUAL_JUDGMENT_CONTROL_ENVELOPE_V1::" + family,
        "family": family,
        "benchmark_harness_zero_cost": True,
        "scorer_frozen": True,
        "brain_candidate_bound": True,
        "brain_owned_operative_configuration": True,
        "configuration_materially_constrains_execution": bool(materiality["pass"]),
        "capability_package_contains_configuration": True,
        "promotion_evaluates_brain_configured_system": True,
        "external_hidden_target_capability_provider": False,
        "ownership_claim_relies_on_model_standalone_superiority": False,
        "future_use_requires_capability_rediscovery": False,
        "model_role": "GENERAL_COGNITION_SUBSTRATE",
        "model_dependency_count": 1,
        "model_dependencies_declared": True,
        "general_substrate_test_pass": bool(materiality["pass"]),
        "incremental_spend_usd": 0,
    }

class Tests(unittest.TestCase):
    def test_materiality_precondition_is_true(self):
        out = evaluate_materiality_counterfactual()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["configuration_material_control_proven"])

    def test_finance_route_passes_source_gate_v2(self):
        out = evaluate(route("FINANCIAL_ANALYSIS"))
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["clean_case_execution_authority"])

    def test_unknown_domain_route_passes_source_gate_v2(self):
        out = evaluate(route("UNKNOWN_DOMAIN_ADAPTATION"))
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["clean_case_execution_authority"])

    def test_materiality_removal_fails_closed(self):
        r = route("FINANCIAL_ANALYSIS")
        r["configuration_materially_constrains_execution"] = False
        r["general_substrate_test_pass"] = False
        out = evaluate(r)
        self.assertFalse(out["pass"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN", out["errors"])
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
