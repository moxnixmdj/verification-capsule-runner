import copy
import json
import unittest
from pathlib import Path

from residual_dependency_eliminator import eliminate_payload


ROOT=Path(__file__).resolve().parent
PAYLOAD=json.loads((ROOT/"zero_reality_residual_subtraction_input_v3.json").read_text())


class ThreeTailDeferralIndependentTests(unittest.TestCase):
    def test_frozen_three_tail_input_has_zero_preproof_survivors(self):
        out=eliminate_payload(PAYLOAD)
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(out["implementation_count"],0,out)
        self.assertEqual(out["surviving_residual_ids"],[],out)
        self.assertEqual(len(out["results"]),3)
        self.assertTrue(all(
            r["disposition"]=="PROOF_ONLY_DEFERRED__MEASURE_CURRENT_COMPOSED_ROUTE_FIRST"
            for r in out["results"]
        ))

    def test_each_repeatable_solvable_failure_reopens_only_that_tail(self):
        for i,row in enumerate(PAYLOAD["claims"]):
            p=copy.deepcopy(PAYLOAD)
            p["claims"][i]["repeatable_solvable_terminal_failure_observed"]=True
            out=eliminate_payload(p)
            self.assertEqual(out["status"],"PASS",(i,out))
            self.assertEqual(out["implementation_count"],1,(i,out))
            self.assertEqual(out["surviving_residual_ids"],[row["residual_id"]],(i,out))

    def test_missing_current_route_fails_closed_for_each_tail(self):
        for i in range(3):
            p=copy.deepcopy(PAYLOAD)
            p["claims"][i]["current_composed_route_exists"]=False
            out=eliminate_payload(p)
            self.assertEqual(out["status"],"FAIL_CLOSED",(i,out))
            self.assertEqual(out["surviving_residual_ids"],[],(i,out))

    def test_untraceable_evidence_fails_closed(self):
        p=copy.deepcopy(PAYLOAD)
        p["claims"][0]["evidence"]={"note":"not-a-traceable-authority"}
        out=eliminate_payload(p)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)

    def test_unknown_claim_field_fails_closed(self):
        p=copy.deepcopy(PAYLOAD)
        p["claims"][0]["invented_authority"]=True
        out=eliminate_payload(p)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(out["reason"].startswith("UNKNOWN_CLAIM_FIELDS"),out)


if __name__=="__main__":
    unittest.main()
