import copy, unittest
from verification.rank22_stage_b_verify import load_here, validate

class Rank22StageB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source,cls.contract=load_here()
    def check(self,s=None,c=None):
        return validate(s or self.source,c or self.contract)
    def test_exact_frozen_contract_passes(self):
        self.assertEqual(self.check(),[])
    def test_wrong_edit_wall_fails(self):
        c=copy.deepcopy(self.contract); c["edit_substitutions"]["clip_wall_thickness"]=1.0
        self.assertTrue(any(x.startswith("EDIT_INVARIANTS") for x in self.check(c=c)))
    def test_undeclared_edit_fails(self):
        c=copy.deepcopy(self.contract); c["edit_substitutions"]["clip_width"]=2.0
        self.assertIn("EDIT_KEYS",self.check(c=c))
    def test_missing_tangency_semantics_fails(self):
        c=copy.deepcopy(self.contract)
        c["geometric_semantics"].remove("SLOPED_INNER_LINES_TANGENT_TO_INNER_CONNECTOR_ARCS_AND_INNER_BRIDGE")
        self.assertIn("GEOMETRIC_SEMANTICS",self.check(c=c))
    def test_baked_shape_acceptance_fails(self):
        c=copy.deepcopy(self.contract)
        c["model_requirements"].remove("NO_BAKED_PART_FEATURE_AS_MODEL")
        self.assertIn("MODEL_REQUIREMENTS",self.check(c=c))
    def test_missing_environment_source_fails(self):
        s=copy.deepcopy(self.source); s["authoritative_sources"]=s["authoritative_sources"][:2]
        self.assertIn("SOURCE_SET",self.check(s=s))
    def test_discovery_after_stage_b_fails(self):
        s=copy.deepcopy(self.source); s["information_boundary"]["discovery_search_after_stage_b"]=True
        self.assertIn("INFORMATION_BOUNDARY",self.check(s=s))
    def test_hidden_verifier_read_fails(self):
        s=copy.deepcopy(self.source); s["information_boundary"]["hidden_verifier_read"]=True
        self.assertIn("SOURCE_BOUNDARY_DIRTY",self.check(s=s))
    def test_missing_mutation_coverage_fails(self):
        c=copy.deepcopy(self.contract); c["mutation_kill_set"].remove("BREAK_DECLARED_TANGENCY")
        self.assertIn("MUTATION_COVERAGE",self.check(c=c))

if __name__=="__main__": unittest.main(verbosity=2)
