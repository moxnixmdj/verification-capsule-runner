import copy
import unittest
from scope_equivalent_proof_gate import evaluate

def base():
    return {
      "source_private_or_nonexecutable_surface":"PRIVATE_TARGET",
      "candidate_proof_route":"PUBLIC_ABSOLUTE_ROUTE",
      "required_behavior_ids":["B_CORE","B_QUALITY"],
      "candidate_behavior_ids":["B_CORE","B_QUALITY","B_EXTRA"],
      "required_interaction_ids":["I_CROSS"],
      "candidate_interaction_ids":["I_CROSS","I_EXTRA"],
      "proof_mode":"ABSOLUTE_BEHAVIORAL_PROTOCOL",
      "population_relation":"CANDIDATE_SUPERSET_PROVEN",
      "environment_relation":"CANDIDATE_STRICTER_PROVEN",
      "oracle_relation":"CANDIDATE_STRONGER_PROVEN",
      "relation_receipts":{
        "population":"proof/population.json",
        "environment":"proof/environment.json",
        "oracle":"proof/oracle.json"
      },
      "unresolved_required_dimensions":[],
      "required_subjective_quality_dimensions":["presentation_quality"],
      "candidate_subjective_quality_dimensions":["presentation_quality"],
      "zero_incremental_spend":True,
      "independent_acceptance":True,
      "contamination_safe":True,
      "candidate_route_owned_or_noncapability_jit_only":True,
      "opaque_target_capability_provider":False,
      "target_weakened":False
    }

class IndependentGateVerification(unittest.TestCase):
    def test_full_stronger_route_admitted(self):
        r=evaluate(base())
        self.assertTrue(r["admissible"],r)
        self.assertEqual(r["status"],"ADMISSIBLE_SUBSTITUTION")

    def test_each_missing_required_behavior_fails(self):
        for missing in ["B_CORE","B_QUALITY"]:
            x=base()
            x["candidate_behavior_ids"]=[b for b in x["candidate_behavior_ids"] if b!=missing]
            r=evaluate(x)
            self.assertFalse(r["admissible"],(missing,r))

    def test_interaction_coverage_required(self):
        x=base(); x["candidate_interaction_ids"]=["I_EXTRA"]
        self.assertFalse(evaluate(x)["admissible"])

    def test_nonexact_relations_require_receipts(self):
        for relation in ["population","environment","oracle"]:
            x=base(); x["relation_receipts"].pop(relation)
            self.assertFalse(evaluate(x)["admissible"],relation)

    def test_exact_relations_need_no_implication_receipts(self):
        x=base()
        x["population_relation"]="EXACT"
        x["environment_relation"]="EXACT"
        x["oracle_relation"]="EXACT"
        x["relation_receipts"]={}
        self.assertTrue(evaluate(x)["admissible"])

    def test_unproved_relation_fails(self):
        for key in ["population_relation","environment_relation","oracle_relation"]:
            x=base(); x[key]="SIMILAR_SEEMS_FINE"
            self.assertFalse(evaluate(x)["admissible"],key)

    def test_subjective_quality_not_replaced_by_mechanics(self):
        x=base(); x["candidate_subjective_quality_dimensions"]=[]
        r=evaluate(x)
        self.assertFalse(r["admissible"])
        self.assertTrue(any("MISSING_SUBJECTIVE_QUALITY" in e for e in r["errors"]))

    def test_unresolved_dimension_fails(self):
        x=base(); x["unresolved_required_dimensions"]=["open_ended_quality"]
        self.assertFalse(evaluate(x)["admissible"])

    def test_opaque_provider_fails(self):
        x=base(); x["opaque_target_capability_provider"]=True
        self.assertFalse(evaluate(x)["admissible"])

    def test_target_weakening_fails(self):
        x=base(); x["target_weakened"]=True
        self.assertFalse(evaluate(x)["admissible"])

    def test_zero_cost_is_hard_requirement(self):
        x=base(); x["zero_incremental_spend"]=False
        self.assertFalse(evaluate(x)["admissible"])

    def test_independent_acceptance_is_hard_requirement(self):
        x=base(); x["independent_acceptance"]=False
        self.assertFalse(evaluate(x)["admissible"])

    def test_contamination_safety_is_hard_requirement(self):
        x=base(); x["contamination_safe"]=False
        self.assertFalse(evaluate(x)["admissible"])

    def test_missing_lists_fail_closed(self):
        for key in ["required_behavior_ids","candidate_behavior_ids","required_interaction_ids","candidate_interaction_ids"]:
            x=base(); x.pop(key)
            self.assertFalse(evaluate(x)["admissible"],key)

    def test_duplicate_ids_fail_closed(self):
        x=base(); x["required_behavior_ids"]=["B_CORE","B_CORE"]
        self.assertFalse(evaluate(x)["admissible"])

    def test_gate_never_grants_capability_credit_field(self):
        r=evaluate(base())
        self.assertNotIn("capability_credit",r)
        self.assertNotIn("family_credit",r)

if __name__=="__main__":
    unittest.main()
