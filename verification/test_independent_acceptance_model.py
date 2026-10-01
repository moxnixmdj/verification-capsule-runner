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

if __name__=="__main__":
    unittest.main()
