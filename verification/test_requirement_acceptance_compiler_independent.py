import unittest

from canonical.runtime import independent_acceptance_model as iam
from canonical.runtime.requirement_acceptance_compiler import compile_requirements


class IndependentRequirementAcceptanceCompilerVerification(unittest.TestCase):
    def test_all_declared_transform_kinds_produce_nonempty_independent_consequences(self):
        rows=[
            {
                "id":f"R_{kind}",
                "critical":True,
                "transform_kinds":[kind],
                "builder_dependencies":["raw:source",f"builder:{kind}"],
            }
            for kind in sorted(iam.OBLIGATIONS)
        ]
        out=compile_requirements(rows)
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertEqual(out["requirement_count"],len(iam.OBLIGATIONS))
        for plan in out["plans"]:
            self.assertTrue(plan["required_failure_modes"])
            self.assertEqual(
                len(plan["counterexample_templates"]),
                len(plan["required_failure_modes"]),
            )
            self.assertIn("MUST_NOT_SHARE",plan["independence_rule"])

    def test_unknown_semantic_transform_cannot_be_silently_generalized(self):
        out=compile_requirements([{"id":"R","critical":True,"transform_kinds":["unknown_magic"]}])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["plans"],[])

    def test_duplicate_requirement_identity_fails_closed(self):
        out=compile_requirements([
            {"id":"R","transform_kinds":["artifact"]},
            {"id":"R","transform_kinds":["artifact"]},
        ])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any("REQUIREMENT_ID_DUPLICATE" in x for x in out["errors"]))

    def test_custom_failure_mode_without_independent_template_fails_closed(self):
        out=compile_requirements([{
            "id":"R",
            "transform_kinds":["artifact"],
            "must_detect_failure_modes":["invented_unbacked_mode"],
        }])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any("COUNTEREXAMPLE_TEMPLATE_MISSING" in x for x in out["errors"]))

    def test_invalid_builder_dependency_shape_fails_closed(self):
        out=compile_requirements([{
            "id":"R",
            "transform_kinds":["selection"],
            "builder_dependencies":"shared-builder",
        }])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_compiler_is_not_terminal_authority(self):
        out=compile_requirements([{
            "id":"R",
            "transform_kinds":["geometry_reconstruction"],
            "builder_dependencies":["raw:drawing"],
        }])
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertIs(out["terminal_authority"],False)
        self.assertIn("NO_SEMANTIC_EXTRACTION",out["rule"])

    def test_rank23_relevant_vocab_has_expected_failure_modes(self):
        out=compile_requirements([
            {"id":"A","transform_kinds":["aggregate","artifact"]},
            {"id":"G","transform_kinds":["geometry_reconstruction","selection"]},
            {"id":"S","transform_kinds":["state_transition"]},
        ])
        self.assertEqual(out["status"],"COMPILED",out)
        by={p["requirement_id"]:set(p["required_failure_modes"]) for p in out["plans"]}
        self.assertIn("component_omission",by["A"])
        self.assertIn("topology",by["G"])
        self.assertIn("failure_recovery",by["S"])


if __name__=="__main__":
    unittest.main()
