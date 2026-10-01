import unittest
from independent_acceptance_model import assess, OBLIGATIONS

class TestIndependentAcceptanceModel(unittest.TestCase):
    def test_correlated_recompute_rejected(self):
        m={"requirements":[{"id":"R","transform_kinds":["aggregate"],"builder_dependencies":["raw:x","semantic:A"]}],
           "checks":[{"id":"same","covers":["R"],"provenance":"same_formula","dependencies":["raw:x","semantic:A"],"detects":["aggregation_formula"]}]}
        o=assess(m)
        self.assertFalse(o["pass"])
        self.assertIn("R",o["failed_requirements"])

    def test_full_independent_coverage_passes(self):
        modes=list(OBLIGATIONS["aggregate"])
        m={"requirements":[{"id":"R","transform_kinds":["aggregate"],"builder_dependencies":["raw:x","builder:A"]}],
           "checks":[{"id":"alt","covers":["R"],"provenance":"independent_oracle","dependencies":["raw:x","oracle:B"],"detects":modes}]}
        self.assertTrue(assess(m)["pass"])

    def test_any_shared_nonraw_dependency_rejects(self):
        for dep in ["semantic:S","builder:F","implementation:X","oracle:Q"]:
            m={"requirements":[{"id":"R","must_detect_failure_modes":["x"],"builder_dependencies":["raw:i",dep]}],
               "checks":[{"id":"C","covers":["R"],"provenance":"independent_oracle","dependencies":["raw:i",dep],"detects":["x"]}]}
            o=assess(m)
            self.assertFalse(o["pass"],dep)
            reasons=o["requirements"][0]["rejected_checks"][0]["reasons"]
            self.assertTrue(any("SHARED_NONRAW_DEPENDENCIES" in r for r in reasons),dep)

    def test_every_transform_kind_fails_closed_without_checks(self):
        for kind in OBLIGATIONS:
            o=assess({"requirements":[{"id":kind,"transform_kinds":[kind],"builder_dependencies":[]}],"checks":[]})
            self.assertFalse(o["pass"],kind)
            self.assertTrue(o["requirements"][0]["counterexample_templates"],kind)

    def test_noncritical_requirement_does_not_block(self):
        o=assess({"requirements":[{"id":"N","critical":False,"transform_kinds":["aggregate"],"builder_dependencies":[]}],"checks":[]})
        self.assertTrue(o["pass"])

    def test_precommitted_bun_spent_heldout_blocks_correlated_self_tests(self):
        # Heldout selected before reading failure details. This model uses only
        # PR240's PRE-verifier plan: candidate-authored baseline/runtime/map
        # self-tests derived from the same release-policy interpretation.
        m={
          "requirements":[{
            "id":"BUN_PUBLIC_RELEASE_POLICY_ENVELOPE",
            "critical":True,
            "must_detect_failure_modes":["policy_or_semantic_variant"],
            "builder_dependencies":["raw:instruction","raw:visibility-policy","semantic:release-policy-interpretation"],
          }],
          "checks":[
            {
              "id":"candidate-self-test-functional-output",
              "covers":["BUN_PUBLIC_RELEASE_POLICY_ENVELOPE"],
              "provenance":"builder_derived",
              "dependencies":["raw:instruction","semantic:release-policy-interpretation"],
              "detects":["baseline_functional_output"],
            },
            {
              "id":"candidate-self-test-map-and-manifest",
              "covers":["BUN_PUBLIC_RELEASE_POLICY_ENVELOPE"],
              "provenance":"builder_derived",
              "dependencies":["raw:visibility-policy","semantic:release-policy-interpretation"],
              "detects":["baseline_provenance_scan","manifest_consistency"],
            },
          ],
        }
        out=assess(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["failed_requirements"],["BUN_PUBLIC_RELEASE_POLICY_ENVELOPE"])
        r=out["requirements"][0]
        self.assertEqual(r["uncovered"],("policy_or_semantic_variant",))
        self.assertEqual(r["independent_checks"],())

if __name__=="__main__":
    unittest.main()


def test_rank21_semantic_risk_is_blocked_without_measurement_specific_checks():
    model = {
        "requirements": [{
            "id": "LSC",
            "critical": True,
            "transform_kinds": ["numeric_formula", "selection", "measurement_calibration", "signal_correction", "method_model_selection"],
            "builder_dependencies": ["raw:counts", "raw:sample", "semantic:lsc-method-a"],
        }],
        "checks": [{
            "id": "old-stage-b-checks",
            "covers": ["LSC"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:counts", "raw:sample", "oracle:arithmetic"],
            "detects": [
                "unit_or_scale", "boundary_or_extreme", "alternate_derivation",
                "ordering_precedence", "missing_value", "tie_or_duplicate", "fallback_scope"
            ],
        }],
    }
    out = assess(model)
    assert out["pass"] is False
    r = out["requirements"][0]
    for mode in (
        "standard_composition","measurement_channel_scope",
        "cross_talk_direction","correction_parameter_identity",
        "method_variant","assumptions_to_formula",
    ):
        assert mode in r["uncovered"]


def test_measurement_semantics_complete_independent_plan_can_pass():
    kinds = ["measurement_calibration", "signal_correction", "method_model_selection"]
    required = set()
    for kind in kinds:
        required.update(OBLIGATIONS[kind])
    model = {
        "requirements": [{
            "id": "M",
            "critical": True,
            "transform_kinds": kinds,
            "builder_dependencies": ["raw:observations", "builder:method-a"],
        }],
        "checks": [{
            "id": "physical-model-challenger",
            "covers": ["M"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:observations", "oracle:physical-method-b"],
            "detects": sorted(required),
        }],
    }
    out = assess(model)
    assert out["pass"] is True
