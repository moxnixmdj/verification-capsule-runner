import unittest
from copy import deepcopy

from terminal_closure_reducer import evaluate_manifest


def passing_manifest():
    families=[{"id":f"FAMILY_{i:02d}","closure_state":"PASS"} for i in range(19)]
    return {
        "expected_family_count":19,
        "actual_family_count":19,
        "families":families,
        "counters":{
            "uncontracted_required_behaviors":0,
            "unproved_required_behaviors":0,
            "donor_dependent_required_behaviors":0,
            "unresolved_verifier_mutations":0,
            "unresolved_composition_failures":0,
            "contaminated_promotion_evidence":0,
            "resource_or_authority_violations":0,
        },
        "terminal_predicates":{
            "exact_target_family_count_19":True,
            "every_required_behavior_contracted":True,
            "every_required_behavior_has_admissible_proof":True,
            "donor_dependent_required_behaviors_zero":True,
            "unexplained_required_behaviors_zero":True,
            "unresolved_verifier_mutations_zero":True,
            "unresolved_composition_failures_zero":True,
            "contaminated_evidence_used_for_promotion_zero":True,
            "resource_or_authority_violations_zero":True,
            "all_frozen_opus_acceptance_predicates_pass":True,
            "final_donor_deletion_cleanroom_pass":True,
            "proof_bundle_frozen":True,
        },
    }


class TerminalClosureTests(unittest.TestCase):
    def test_complete_passes(self):
        out=evaluate_manifest(passing_manifest())
        self.assertTrue(out["achieved"])
        self.assertEqual(out["failed_predicates"],[])

    def test_every_single_terminal_predicate_fails_closed(self):
        base=passing_manifest()
        for key in list(base["terminal_predicates"]):
            m=deepcopy(base)
            m["terminal_predicates"][key]=False
            out=evaluate_manifest(m)
            self.assertFalse(out["achieved"],key)

    def test_every_counter_nonzero_and_unknown_fails_closed(self):
        base=passing_manifest()
        for key in list(base["counters"]):
            for bad in (1,None):
                m=deepcopy(base)
                m["counters"][key]=bad
                out=evaluate_manifest(m)
                self.assertFalse(out["achieved"],(key,bad))

    def test_open_family_fails(self):
        m=passing_manifest()
        m["families"][0]["closure_state"]="OPEN"
        self.assertFalse(evaluate_manifest(m)["achieved"])

    def test_duplicate_family_fails(self):
        m=passing_manifest()
        m["families"][18]["id"]=m["families"][0]["id"]
        self.assertFalse(evaluate_manifest(m)["achieved"])

    def test_count_mismatch_fails(self):
        m=passing_manifest()
        m["families"].pop()
        m["actual_family_count"]=18
        self.assertFalse(evaluate_manifest(m)["achieved"])

    def test_counter_predicate_contradiction_fails(self):
        m=passing_manifest()
        m["counters"]["donor_dependent_required_behaviors"]=1
        out=evaluate_manifest(m)
        self.assertFalse(out["achieved"])
        self.assertTrue(any(x.startswith("COUNTER_PREDICATE_CONTRADICTION") for x in out["failed_predicates"]))


if __name__=="__main__":
    unittest.main()
