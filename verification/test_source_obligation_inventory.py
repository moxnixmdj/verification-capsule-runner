import unittest
from verification.source_obligation_inventory import (
    inventory_source_obligations, validate_source_coverage, RequirementBinding
)
from verification.spent_acceptance_sources import RANK12,RANK13

class SourceObligationTests(unittest.TestCase):
    def test_rank12_future_variation_is_inventory_obligation(self):
        obs=inventory_source_obligations(RANK12,"rank12/instruction.md")
        excerpts=[o.excerpt for o in obs]
        target=[o for o in obs if "Future target directories may have different numbers" in o.excerpt]
        self.assertEqual(len(target),1,excerpts)
        o=target[0]
        self.assertIn("FUTURE",o.tags)
        self.assertIn("DIFFERENT",o.tags)
        self.assertIn("MISSING_OPTIONAL",o.tags)

    def test_rank12_example_only_acceptance_fails_closed(self):
        obs=inventory_source_obligations(RANK12,"rank12/instruction.md")
        errors=validate_source_coverage(obs,[])
        self.assertTrue(any(e.startswith("UNMAPPED_SOURCE_OBLIGATION:") for e in errors))
        bindings=[
            RequirementBinding(
                requirement_id=f"REQ-{i}",
                source_obligation_ids=(o.obligation_id,),
                scenario_kinds=("VISIBLE_EXAMPLE_REPLAY",),
            )
            for i,o in enumerate(obs)
        ]
        errors=validate_source_coverage(obs,bindings)
        self.assertTrue(any(e.startswith("SCOPE_CLAIM_WITHOUT_NONEXAMPLE_SCENARIO:") for e in errors))

    def test_rank12_generative_binding_closes_scope_gate(self):
        obs=inventory_source_obligations(RANK12,"rank12/instruction.md")
        bindings=[
            RequirementBinding(
                requirement_id=f"REQ-{i}",
                source_obligation_ids=(o.obligation_id,),
                scenario_kinds=("HELDOUT_VARIATION",),
            )
            for i,o in enumerate(obs)
        ]
        self.assertEqual(validate_source_coverage(obs,bindings),[])

    def test_rank13_guard_does_not_claim_domain_method_semantics(self):
        obs=inventory_source_obligations(RANK13,"rank13/instruction.md")
        self.assertFalse(any(
            "supervisory duration" in o.excerpt.lower() and "credit derivative" in o.excerpt.lower()
            for o in obs
        ))
        self.assertTrue(all("SA_CCR_METHOD_RULES" not in o.tags for o in obs))

    def test_unknown_binding_is_rejected(self):
        obs=inventory_source_obligations("Future files may differ.","x")
        errors=validate_source_coverage(
            obs,
            [RequirementBinding("REQ-X",("SRC-deadbeef",),("HELDOUT_VARIATION",))]
        )
        self.assertTrue(any(e.startswith("UNKNOWN_SOURCE_OBLIGATION:") for e in errors))

if __name__=="__main__":
    unittest.main()
