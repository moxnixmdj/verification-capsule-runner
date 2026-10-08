from __future__ import annotations
import pathlib
import unittest

from canonical.runtime.bounded_explicit_categorical_support_v1 import classify_support, parse_relation
from canonical.runtime.selected_support_truth_certificate_v5 import evaluate as support_truth
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as realize
from canonical.runtime.synthesis_grounded_expression_ir_v1 import INPUT_SCHEMA

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def support_payload(claim,evidence):
    return {"predicate_id":"X","claim":{"claim_id":"C","text":claim,"required":True},"evidence":evidence}

def constraints(max_items=4):
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":max_items,"max_chars":5000,"heading_level":2,"require_title":False}

def realization_payload(claim,evidence):
    return {"v3_input":{"schema":INPUT_SCHEMA,"task":{
      "claims":[{"claim_id":"C1","text":claim,"required":True}],
      "evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}}

class CategoricalKernelTests(unittest.TestCase):
    def test_direct_membership(self):
        out=classify_support("Tweety is a member of Bird.",[
            {"evidence_id":"E1","text":"Report states that Tweety is a member of Bird."}
        ])
        self.assertEqual(out["relation"],"SUPPORTS")
        self.assertEqual(out["support_evidence_ids"],["E1"])

    def test_transitive_membership_proof_path(self):
        out=classify_support("Tweety is a member of Animal.",[
            {"evidence_id":"E1","text":"Report states that Tweety is a member of Canary."},
            {"evidence_id":"E2","text":"Taxonomy states that Canary is a subclass of Bird."},
            {"evidence_id":"E3","text":"Taxonomy states that Bird is a subclass of Animal."},
        ])
        self.assertEqual(out["relation"],"SUPPORTS")
        self.assertEqual(out["support_proof_paths"],[["E1","E2","E3"]])

    def test_negative_membership_propagates_downward_not_upward(self):
        down=classify_support("Tweety is not a member of Canary.",[
            {"evidence_id":"E1","text":"Report states that Tweety is not a member of Animal."},
            {"evidence_id":"E2","text":"Taxonomy states that Canary is a subclass of Animal."},
        ])
        self.assertEqual(down["relation"],"SUPPORTS")
        up=classify_support("Tweety is not a member of Animal.",[
            {"evidence_id":"E1","text":"Report states that Tweety is not a member of Canary."},
            {"evidence_id":"E2","text":"Taxonomy states that Canary is a subclass of Animal."},
        ])
        self.assertEqual(up["relation"],"UNRELATED")

    def test_positive_conflict_via_negative_superclass(self):
        out=classify_support("Tweety is a member of Canary.",[
            {"evidence_id":"E1","text":"A states that Tweety is a member of Canary."},
            {"evidence_id":"E2","text":"B states that Tweety is not a member of Animal."},
            {"evidence_id":"E3","text":"T states that Canary is a subclass of Animal."},
        ])
        self.assertEqual(out["relation"],"BOTH")
        self.assertEqual(out["support_evidence_ids"],["E1"])
        self.assertEqual(out["conflict_evidence_ids"],["E2","E3"])

    def test_cycles_terminate(self):
        out=classify_support("x is a member of b.",[
            {"evidence_id":"E1","text":"R states that x is a member of a."},
            {"evidence_id":"E2","text":"T states that a is a subclass of b."},
            {"evidence_id":"E3","text":"T states that b is a subclass of a."},
        ])
        self.assertEqual(out["relation"],"SUPPORTS")
        self.assertEqual(out["support_evidence_ids"],["E1","E2"])

    def test_transitive_non_subset_proof_is_soundly_exposed(self):
        rows=[
            {"evidence_id":"E1","text":"T states that Canary is a subclass of Bird."},
            {"evidence_id":"E2","text":"T states that Bird is a subclass of Animal."},
            {"evidence_id":"E3","text":"T states that Animal is a subclass of Living."},
            {"evidence_id":"E4","text":"T states that Canary is not a subclass of Living."},
        ]
        p=classify_support("Bird is a subclass of Animal.",rows)
        self.assertEqual(p["relation"],"BOTH")
        self.assertEqual(p["support_evidence_ids"],["E2"])
        self.assertEqual(set(p["conflict_evidence_ids"]),{"E1","E3","E4"})
        n=classify_support("Bird is not a subclass of Animal.",rows)
        self.assertEqual(n["relation"],"BOTH")
        self.assertEqual(set(n["support_evidence_ids"]),{"E1","E3","E4"})
        self.assertEqual(n["conflict_evidence_ids"],["E2"])

    def test_reflexive_negative_subset_fails_closed(self):
        out=classify_support("Bird is not a subset of Bird.",[
            {"evidence_id":"E1","text":"T states that Bird is not a subset of Bird."}
        ])
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["relation"],"UNKNOWN")
        self.assertFalse(out["terminal_authority"])

    def test_namespaced_terms_preserved(self):
        out=parse_relation("ex:Tweety is a member of ex:Bird.")
        self.assertEqual(out["status"],"RESOLVED")
        self.assertEqual(out["subject"],"ex:tweety")
        self.assertEqual(out["category"],"ex:bird")
        self.assertIsNone(out["source"])
        prefixed=parse_relation("Taxonomy: ex:Canary is a subclass of ex:Bird.")
        self.assertEqual(prefixed["status"],"RESOLVED")
        self.assertEqual(prefixed["subclass"],"ex:canary")
        self.assertEqual(prefixed["superclass"],"ex:bird")
        self.assertEqual(prefixed["source"],"Taxonomy")

    def test_uncontrolled_every_form_not_claimed(self):
        out=parse_relation("Every canary is a bird.")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertFalse(out["claim_in_scope"])

    def test_quantified_explicit_member_form_not_claimed(self):
        out=parse_relation("Every canary is a member of Bird.")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertFalse(out["claim_in_scope"])

class SupportPortfolioTests(unittest.TestCase):
    def test_transitive_categorical_support_enters_v5(self):
        out=support_truth(support_payload("Tweety is a member of Animal.",[
            ev("E1","Report states that Tweety is a member of Canary."),
            ev("E2","Taxonomy states that Canary is a subclass of Bird."),
            ev("E3","Taxonomy states that Bird is a subclass of Animal."),
        ]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertEqual(out["support_evidence_ids"],["E1","E2","E3"])

    def test_categorical_conflict_blocks_assertion(self):
        out=support_truth(support_payload("Tweety is a member of Canary.",[
            ev("E1","A states that Tweety is a member of Canary."),
            ev("E2","B states that Tweety is not a member of Animal."),
            ev("E3","T states that Canary is a subclass of Animal."),
        ]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["predicate_truth"],"FALSE")
        self.assertEqual(out["conflict_evidence_ids"],["E2","E3"])

    def test_unchecked_extra_evidence_preserves_unknown(self):
        out=support_truth(support_payload("Tweety is a member of Bird.",[
            ev("E1","Report states that Tweety is a member of Bird."),
            ev("E2","This prose has no checked semantic relation."),
        ]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")
        self.assertEqual(out["unresolved_evidence_ids"],["E2"])

    def test_categorical_paraphrase_preserves_unknown(self):
        out=support_truth(support_payload("Tweety is a member of Bird.",[
            ev("E1","Report states that Tweety is a member of Bird."),
            ev("E2","Report states that Tweety does not belong to Bird."),
        ]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")
        self.assertEqual(out["unresolved_evidence_ids"],["E2"])

    def test_numeric_v4_regression(self):
        out=support_truth(support_payload("Revenue growth is at least 10.",[
            ev("E1","Report states Revenue growth is 12.")
        ]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertEqual(out["relation_audit"][0]["grammar"],"NUMERIC_RELATION_V1")

    def test_source_defined_equivalence_regression(self):
        out=support_truth(support_payload("The release date is June.",[
            ev("E1","Launch date means release date. Report states that The launch date is June.")
        ]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["predicate_truth"],"TRUE")

class GroundedRealizationTests(unittest.TestCase):
    def test_transitive_categorical_claim_realizes_with_provenance(self):
        out=realize(realization_payload("Tweety is a member of Animal.",[
            ev("E1","Report states that Tweety is a member of Canary.","REPORT"),
            ev("E2","Taxonomy states that Canary is a subclass of Bird.","TAX"),
            ev("E3","Taxonomy states that Bird is a subclass of Animal.","TAX"),
        ]))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["rendered_text"],"- Tweety is a member of Animal. [src:REPORT@p1;TAX@p1]")
        self.assertFalse(out["source_authorization_verified"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["db_admission_authority"])
        self.assertFalse(out["u_subtraction_authority"])
        self.assertFalse(out["terminal_authority"])

class AdmissionStaticBoundaryTests(unittest.TestCase):
    def test_v6_wires_only_v3_required_realization_successor(self):
        path=pathlib.Path("canonical/runtime/p3_real_context_v3_admission_v6.py")
        text=path.read_text(encoding="utf-8")
        self.assertIn("p3_required_claim_grounded_realization_cell_v3",text)
        self.assertIn('SCHEMA="PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V6"',text)
        self.assertIn("REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3",text)
        self.assertIn('"terminal_authority":False',text)
        self.assertNotIn('"terminal_credit_delta":1',text.replace(" ",""))

if __name__=="__main__":
    unittest.main(verbosity=2)
