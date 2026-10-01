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


from requirement_graph_kernel import compile_requirement_contract, requirement_mutation_score

class TestRequirementGraphKernelIndependent(unittest.TestCase):
    @staticmethod
    def corpus():
        return [
            {"id":"REQ-INPUT","critical":True,"dependencies":[],"children":[],"open_questions":[],
             "clauses":[{"id":"C-IN","keyword":"MUST","covered_by_scenarios":["S-IN"]}],
             "scenarios":[{"id":"S-IN","given":["raw input"],"when":["normalize"],"then":["normalized input exists"]}]},
            {"id":"REQ-CALC","critical":True,"dependencies":["REQ-INPUT"],"children":[],"open_questions":[],
             "clauses":[{"id":"C-CALC","keyword":"MUST","covered_by_scenarios":["S-CALC"]}],
             "scenarios":[{"id":"S-CALC","given":["normalized input"],"when":["calculate"],"then":["intermediate and output trace exists"]}]},
            {"id":"REQ-CHECK","critical":True,"dependencies":["REQ-CALC"],"children":[],"open_questions":[],
             "clauses":[{"id":"C-CHECK","keyword":"MUST","covered_by_scenarios":["S-CHECK"]}],
             "scenarios":[{"id":"S-CHECK","given":["candidate output"],"when":["independent check"],"then":["observable acceptance consequence"]}]},
        ]

    def test_valid_contract(self):
        self.assertTrue(compile_requirement_contract(
            self.corpus(), expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_delete_each_required_node_fails(self):
        expected=["REQ-INPUT","REQ-CALC","REQ-CHECK"]
        for i in range(3):
            c=self.corpus(); c.pop(i)
            self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])

    def test_ambiguity_uncovered_clause_dangling_and_cycle_fail(self):
        expected=["REQ-INPUT","REQ-CALC","REQ-CHECK"]
        c=self.corpus(); c[1]["open_questions"]=["which formula applies?"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])
        c=self.corpus(); c[1]["clauses"][0]["covered_by_scenarios"]=[]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])
        c=self.corpus(); c[2]["dependencies"]=["REQ-NOPE"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])
        c=self.corpus(); c[0]["dependencies"]=["REQ-CHECK"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])

    def test_seeded_mutations_all_killed(self):
        score=requirement_mutation_score(self.corpus())
        self.assertTrue(score["pass"])
        self.assertEqual(score["survived"],0)
        self.assertEqual(score["kill_fraction"],1.0)
        self.assertGreaterEqual(score["total"],8)

if __name__=="__main__":
    unittest.main()
