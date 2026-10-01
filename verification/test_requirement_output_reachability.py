import unittest
from requirement_graph_kernel import (
    validate_requirement_output_reachability,
    compile_structured_method_contract,
)

class OutputReachabilityTests(unittest.TestCase):
    def _req(self, rid):
        return {
            "id":rid,"critical":True,"dependencies":[],"children":[],"open_questions":[],
            "clauses":[{"id":rid+"-C1","keyword":"MUST","covered_by_scenarios":[rid+"-S"]}],
            "scenarios":[{"id":rid+"-S","given":["raw"],"when":["transform"],"then":["observable"]}],
        }

    def test_spent_saccr_shortcut_missing_duration_fails(self):
        reqs=[self._req("NOTIONAL"),self._req("SUPERVISORY_DURATION"),self._req("MATURITY_FACTOR"),self._req("SUPERVISORY_FACTOR")]
        nodes=[
            {"id":"n","requirement_id":"NOTIONAL"},
            {"id":"sd","requirement_id":"SUPERVISORY_DURATION"},
            {"id":"mf","requirement_id":"MATURITY_FACTOR"},
            {"id":"sf","requirement_id":"SUPERVISORY_FACTOR"},
            {"id":"shortcut"},{"id":"out"},
        ]
        edges=[
            {"from":"n","to":"shortcut"},{"from":"mf","to":"shortcut"},
            {"from":"sf","to":"shortcut"},{"from":"shortcut","to":"out"},
        ]
        out=validate_requirement_output_reachability(reqs,calculation_nodes=nodes,calculation_edges=edges,outputs=["out"])
        self.assertFalse(out["pass"])
        self.assertIn("SUPERVISORY_DURATION:NO_OUTPUT_PATH",out["uncovered"])

    def test_corrected_lineage_passes(self):
        reqs=[self._req("A"),self._req("B")]
        nodes=[
            {"id":"a","requirement_id":"A"},{"id":"b","requirement_id":"B"},
            {"id":"mid"},{"id":"out"},
        ]
        edges=[{"from":"a","to":"mid"},{"from":"b","to":"mid"},{"from":"mid","to":"out"}]
        out=compile_structured_method_contract(
            reqs,expected_required_ids=["A","B"],
            calculation_nodes=nodes,calculation_edges=edges,outputs=["out"]
        )
        self.assertTrue(out["pass"])

    def test_cad_local_only_fails_global_requirements(self):
        reqs=[{"id":"LOCAL_DIM"},{"id":"GLOBAL_TOPOLOGY"},{"id":"GLOBAL_ENVELOPE"}]
        nodes=[
            {"id":"local","requirement_id":"LOCAL_DIM"},
            {"id":"topo","requirement_id":"GLOBAL_TOPOLOGY"},
            {"id":"env","requirement_id":"GLOBAL_ENVELOPE"},
            {"id":"out"},
        ]
        out=validate_requirement_output_reachability(
            reqs,calculation_nodes=nodes,
            calculation_edges=[{"from":"local","to":"out"}],outputs=["out"]
        )
        self.assertFalse(out["pass"])
        self.assertIn("GLOBAL_TOPOLOGY:NO_OUTPUT_PATH",out["uncovered"])
        self.assertIn("GLOBAL_ENVELOPE:NO_OUTPUT_PATH",out["uncovered"])

    def test_cycle_dangling_and_empty_exclusion_fail_closed(self):
        reqs=[{"id":"R"}]
        nodes=[{"id":"r","requirement_id":"R"},{"id":"a"},{"id":"out"}]
        edges=[{"from":"r","to":"a"},{"from":"a","to":"r"},{"from":"ghost","to":"out"}]
        out=validate_requirement_output_reachability(
            reqs,calculation_nodes=nodes,calculation_edges=edges,outputs=["out"],
            exclusions=[{"requirement_id":"R","justification":""}]
        )
        codes={d["code"] for d in out["diagnostics"]}
        self.assertFalse(out["pass"])
        self.assertIn("calculation-cycle",codes)
        self.assertIn("dangling-calculation-edge",codes)
        self.assertIn("empty-exclusion-justification",codes)

if __name__=="__main__":
    unittest.main(verbosity=2)
