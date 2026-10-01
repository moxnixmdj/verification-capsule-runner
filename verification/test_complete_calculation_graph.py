import unittest
from complete_calculation_graph import validate

class CompleteCalculationGraphTests(unittest.TestCase):
    def test_complete_graph_passes(self):
        m={"requirements":[{"id":"R1"},{"id":"R2"}],
           "nodes":[{"id":"r1","requirement_id":"R1"},{"id":"r2","requirement_id":"R2"},{"id":"mid"},{"id":"out"}],
           "edges":[{"from":"r1","to":"mid"},{"from":"r2","to":"mid"},{"from":"mid","to":"out"}],
           "outputs":["out"],"exclusions":[]}
        self.assertTrue(validate(m)["pass"])

    def test_spent_saccr_shortcut_fails(self):
        m={"requirements":[{"id":"NOTIONAL"},{"id":"SUPERVISORY_DURATION"},{"id":"MATURITY_FACTOR"},{"id":"SUPERVISORY_FACTOR"}],
           "nodes":[{"id":"n","requirement_id":"NOTIONAL"},{"id":"sd","requirement_id":"SUPERVISORY_DURATION"},
                    {"id":"mf","requirement_id":"MATURITY_FACTOR"},{"id":"sf","requirement_id":"SUPERVISORY_FACTOR"},
                    {"id":"shortcut"},{"id":"out"}],
           "edges":[{"from":"n","to":"shortcut"},{"from":"mf","to":"shortcut"},{"from":"sf","to":"shortcut"},{"from":"shortcut","to":"out"}],
           "outputs":["out"],"exclusions":[]}
        out=validate(m)
        self.assertFalse(out["pass"])
        self.assertIn("SUPERVISORY_DURATION:NO_OUTPUT_PATH", out["uncovered"])

    def test_corrected_saccr_lineage_passes(self):
        m={"requirements":[{"id":"NOTIONAL"},{"id":"SUPERVISORY_DURATION"},{"id":"MATURITY_FACTOR"},{"id":"SUPERVISORY_FACTOR"}],
           "nodes":[{"id":"n","requirement_id":"NOTIONAL"},{"id":"sd","requirement_id":"SUPERVISORY_DURATION"},
                    {"id":"mf","requirement_id":"MATURITY_FACTOR"},{"id":"sf","requirement_id":"SUPERVISORY_FACTOR"},
                    {"id":"effective_notional"},{"id":"addon"},{"id":"out"}],
           "edges":[{"from":"n","to":"effective_notional"},{"from":"sd","to":"effective_notional"},
                    {"from":"mf","to":"effective_notional"},{"from":"effective_notional","to":"addon"},
                    {"from":"sf","to":"addon"},{"from":"addon","to":"out"}],
           "outputs":["out"],"exclusions":[]}
        self.assertTrue(validate(m)["pass"])

    def test_cad_local_only_fails_global_requirements(self):
        m={"requirements":[{"id":"LOCAL_DIM"},{"id":"GLOBAL_TOPOLOGY"},{"id":"GLOBAL_ENVELOPE"}],
           "nodes":[{"id":"local","requirement_id":"LOCAL_DIM"},{"id":"topo","requirement_id":"GLOBAL_TOPOLOGY"},
                    {"id":"env","requirement_id":"GLOBAL_ENVELOPE"},{"id":"out"}],
           "edges":[{"from":"local","to":"out"}],"outputs":["out"],"exclusions":[]}
        out=validate(m)
        self.assertIn("GLOBAL_TOPOLOGY:NO_OUTPUT_PATH", out["uncovered"])
        self.assertIn("GLOBAL_ENVELOPE:NO_OUTPUT_PATH", out["uncovered"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
