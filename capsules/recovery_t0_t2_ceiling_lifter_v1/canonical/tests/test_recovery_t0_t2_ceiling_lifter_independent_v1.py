from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text())

PATHS={
"protocols":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
"registry":"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
"predicates":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
"binding":"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json",
"terminal":"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json",
"relation":"canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json",
}

def docs():
    return {k:load(v) for k,v in PATHS.items()}

class IndependentRecoveryCeilingTests(unittest.TestCase):
    def test_exact_capsule_yields_candidate_ceiling(self):
        out=evaluate(**docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["source_case_count"],60)
        w=out["candidate_witness"]
        self.assertEqual(w["scope_relation"],"PROVEN_STRONGER")
        self.assertTrue(w["closes_entire_protocol"])
        self.assertEqual(w["result"]["brain_lower_bound"],1.0)
        self.assertEqual(w["result"]["theoretical_upper_bound"],1.0)
        self.assertEqual(w["hard_invariants"]["critical_fail_closed_misses"]["brain_upper_bound"],0.0)
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

    def test_contaminated_receipt_fails_closed(self):
        d=docs()
        d["terminal"]=copy.deepcopy(d["terminal"])
        rows=d["terminal"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
        hit=next(x for x in rows if x.get("behavior_id")=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        hit["tuning_replay"]=True
        out=evaluate(**d)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_RECEIPT_CONTAMINATED:T0",out["errors"])

    def test_scope_dimension_drift_fails_closed(self):
        d=docs()
        d["protocols"]=copy.deepcopy(d["protocols"])
        p=next(x for x in d["protocols"]["protocols"] if x.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        p["task_dimensions"]=p["task_dimensions"][:-1]
        out=evaluate(**d)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_TASK_DIMENSIONS_DRIFT",out["errors"])

    def test_relation_missing_dimension_fails_closed(self):
        d=docs()
        d["relation"]=copy.deepcopy(d["relation"])
        d["relation"]["target_dimension_to_source_checks"].pop("repair selection")
        out=evaluate(**d)
        self.assertFalse(out["pass"])
        self.assertIn("RELATION_DIMENSION_MAP_INCOMPLETE",out["errors"])

    def test_terminal_case_count_drift_fails_closed(self):
        d=docs()
        d["terminal"]=copy.deepcopy(d["terminal"])
        rows=d["terminal"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T2"]
        hit=next(x for x in rows if x.get("behavior_id")=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        hit["case_id"]=hit["case_id"].rsplit("::",1)[0]+"::29"
        out=evaluate(**d)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_CASE_COUNT_DRIFT:T2",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
