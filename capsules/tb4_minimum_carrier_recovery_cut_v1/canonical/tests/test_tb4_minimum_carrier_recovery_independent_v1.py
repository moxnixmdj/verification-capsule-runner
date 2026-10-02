from __future__ import annotations
import copy, os, unittest
from pathlib import Path
from canonical.runtime.tb4_minimum_carrier_recovery_independent_verifier_v1 import (
    SPEC, COMPAT, MANIFEST, ATTAIN, blob_sha, evaluate, load
)

SOURCE_ROOT = Path(os.environ.get("TB4_SOURCE_ROOT", "/tmp/tb4"))

class TB4MinimumCarrierIndependentTests(unittest.TestCase):
    def docs(self):
        return (
            load(SPEC), load(COMPAT), load(MANIFEST), load(ATTAIN), SOURCE_ROOT,
            {"compat": blob_sha(COMPAT), "manifest": blob_sha(MANIFEST), "attain": blob_sha(ATTAIN)},
        )

    def test_live_candidate_reproduces_exact_eight_task_cut(self):
        out = evaluate(*self.docs())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["resource_metadata_independently_reproduced"])
        self.assertEqual(out["minimum_additional_creditable_tasks"], 8)
        self.assertEqual(out["projected_upper_bound_successes"], 220)
        self.assertFalse(out["task_identity_binding"])
        self.assertFalse(out["concrete_carrier_bound"])
        self.assertFalse(out["execution_authority"])

    def test_resource_row_tamper_fails(self):
        docs = list(self.docs())
        docs[0] = copy.deepcopy(docs[0])
        docs[0]["resource_exceed_tasks"][0]["cpus"] = 7
        out = evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_RESOURCE_ROWS_DO_NOT_MATCH_SOURCE", out["errors"])

    def test_seven_task_cut_fails(self):
        docs = list(self.docs())
        docs[0] = copy.deepcopy(docs[0])
        docs[0]["minimum_recovery_set"] = docs[0]["minimum_recovery_set"][:-1]
        out = evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("MINIMUM_RECOVERY_SET_MISMATCH", out["errors"])

    def test_authority_blob_tamper_fails(self):
        docs = list(self.docs())
        docs[0] = copy.deepcopy(docs[0])
        docs[0]["authority"]["attainability_verdict"]["git_blob_sha"] = "0" * 40
        out = evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_BLOB_MISMATCH:attainability_verdict", out["errors"])

    def test_self_authorization_fails(self):
        docs = list(self.docs())
        docs[0] = copy.deepcopy(docs[0])
        docs[0]["verification_state"]["concrete_zero_cost_carrier_bound"] = True
        out = evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_SELF_AUTHORIZATION", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
