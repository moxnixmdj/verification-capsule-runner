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


from specification_consensus_gate import assess_consensus

class TestSpecificationConsensusGateIndependent(unittest.TestCase):
    SOURCE="The service must retain records for 30 days. Logging is informational. If deletion is requested, the service must delete the record within 24 hours."

    @classmethod
    def good(cls):
        a=[
          {"source_sentence_id":"S1","source_quote":"The service must retain records for 30 days.","class":"requirement","requirement_id":"R1","actor":"service","action":"retain","object":"records","constraints":["30 days"]},
          {"source_sentence_id":"S2","source_quote":"Logging is informational.","class":"non_requirement"},
          {"source_sentence_id":"S3","source_quote":"If deletion is requested, the service must delete the record within 24 hours.","class":"requirement","requirement_id":"R2","actor":"service","action":"delete","object":"record","condition":"deletion is requested","constraints":["within 24 hours"]},
        ]
        b=[dict(x) for x in a]
        return [{"extractor_id":"A","sentences":a},{"extractor_id":"B","sentences":b}]

    def test_matching_independent_extractors_pass(self):
        o=assess_consensus(self.SOURCE,self.good())
        self.assertTrue(o["pass"])
        self.assertEqual(len(o["accepted_requirements"]),2)

    def test_missing_source_sentence_fails(self):
        x=self.good(); x[1]["sentences"]=x[1]["sentences"][:-1]
        self.assertFalse(assess_consensus(self.SOURCE,x)["pass"])

    def test_class_disagreement_fails(self):
        x=self.good(); x[1]["sentences"][0]["class"]="non_requirement"
        o=assess_consensus(self.SOURCE,x)
        self.assertFalse(o["pass"])
        self.assertIn("CLASS_DISAGREEMENT:S1",o["failures"])

    def test_semantic_signature_disagreement_fails(self):
        x=self.good(); x[1]["sentences"][2]["constraints"]=["within 48 hours"]
        o=assess_consensus(self.SOURCE,x)
        self.assertFalse(o["pass"])
        self.assertIn("SEMANTIC_SIGNATURE_DISAGREEMENT:S3",o["failures"])

    def test_bad_source_quote_and_single_extractor_fail(self):
        x=self.good(); x[1]["sentences"][0]["source_quote"]="wrong quote"
        self.assertFalse(assess_consensus(self.SOURCE,x)["pass"])
        self.assertFalse(assess_consensus(self.SOURCE,self.good()[:1])["pass"])

if __name__=="__main__":
    unittest.main()
