import unittest
from copy import deepcopy

from terminal_closure_reducer import evaluate_manifest, evaluate_frontier_state


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


def passing_frontier():
    active={
        "atomic_preproof_frontier":{
            "implementation_authority_count":0,
            "execute_now":False,
        }
    }
    universe={
        "atomic_preproof_frontier":{
            "implementation_authority_count":0,
            "execute_now":False,
        },
        "global_cut":{"atomic_preproof_survivor_count":0},
        "execution_authority":{"fresh_terminal_evidence_allowed":True},
    }
    preq={
        "prequalification_progress":{"zero_preproof_implementation_residuals":True},
        "execution_authority":True,
    }
    return active,universe,preq


class TerminalClosureTests(unittest.TestCase):
    def test_complete_passes(self):
        out=evaluate_manifest(passing_manifest())
        self.assertTrue(out["achieved"],out)
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

    def test_valid_frontier_derives_execution_authority(self):
        out=evaluate_frontier_state(*passing_frontier())
        self.assertEqual(out["status"],"PASS",out)
        self.assertTrue(out["execution_authority"],out)
        self.assertTrue(out["fresh_terminal_evidence_allowed"],out)

    def test_frontier_count_contradiction_fails_closed(self):
        args=list(passing_frontier())
        args[0]["atomic_preproof_frontier"]["implementation_authority_count"]=1
        out=evaluate_frontier_state(*args)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertFalse(out["execution_authority"],out)
        self.assertIn("IMPLEMENTATION_AUTHORITY_COUNT_CONTRADICTION:1:0",out["failed_invariants"])

    def test_fresh_evidence_authority_contradiction_fails_closed(self):
        args=list(passing_frontier())
        args[1]["execution_authority"]["fresh_terminal_evidence_allowed"]=False
        out=evaluate_frontier_state(*args)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("FRESH_TERMINAL_EVIDENCE_AUTHORITY_CONTRADICTION",out["failed_invariants"])

    def test_prequalification_zero_preproof_contradiction_fails_closed(self):
        args=list(passing_frontier())
        args[2]["prequalification_progress"]["zero_preproof_implementation_residuals"]=False
        out=evaluate_frontier_state(*args)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("PREQUALIFICATION_ZERO_PREPROOF_CONTRADICTS_ACTIVE_FRONTIER",out["failed_invariants"])


if __name__=="__main__":
    unittest.main()
