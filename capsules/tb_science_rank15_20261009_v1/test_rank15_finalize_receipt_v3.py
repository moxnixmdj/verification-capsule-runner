from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import rank15_finalize_receipt_v3 as m

SAFE="protein-active-learning-trial-0"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"

class Tests(unittest.TestCase):
    def run_case(self, *, cas=False, outcome="skipped", reward=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"execution_guard").mkdir()
            (root/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json").write_text(json.dumps({"status":"TEST","workflow_git_blob_sha":"a"*40}))
            (root/"RANK15_PRESTART_GUARD.json").write_text(json.dumps({"task_read":cas,"pass":cas,"logical_attempt_id":"b"*64}))
            if cas:
                (root/"TERMINAL_SLOT_START_CAS_RECEIPT.json").write_text(json.dumps({
                    "status":"TASK_START_INTENT_COMMITTED","slot_id":SLOT,"task_digest":DIGEST,
                    "key":"terminal-start/x","logical_attempt_id":"b"*64
                }))
            if reward is not None:
                p=root/"jobs"/SAFE/"trial"/"result.json"; p.parent.mkdir(parents=True)
                p.write_text(json.dumps({"verifier_result":{"rewards":{"reward":reward}}}))
            env={"GITHUB_WORKSPACE":str(root),"SAFE_ID":SAFE,"HARBOR_OUTCOME":outcome,"CARRIER_READY":"true","GITHUB_RUN_ID":"1","GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"c"*40}
            with patch.dict(os.environ,env,clear=False): self.assertEqual(m.main(),0)
            return json.loads((root/(SAFE+"__SLOT_RECEIPT_V3.json")).read_text())

    def test_pre_cas_abort_is_nonconsuming(self):
        o=self.run_case()
        self.assertEqual(o["status"],"PREEXPOSURE_ABORT_NONCONSUMING")
        self.assertEqual(o["benchmark_trials_consumed"],0)
        self.assertFalse(o["execution_authority_consumed"])

    def test_success_is_slot_evidence_only(self):
        o=self.run_case(cas=True,outcome="success",reward=1.0)
        self.assertEqual(o["status"],"SUCCESS")
        self.assertEqual(o["consumed_successes_delta"],1)
        self.assertEqual(o["consumed_final_failures_delta"],0)
        self.assertEqual(o["acceptance_credit_delta"],0)
        self.assertEqual(o["terminal_credit_delta"],0)

    def test_started_failure_is_final_zero(self):
        o=self.run_case(cas=True,outcome="failure",reward=0.0)
        self.assertEqual(o["status"],"FINAL_ZERO")
        self.assertEqual(o["consumed_final_failures_delta"],1)
        self.assertEqual(o["benchmark_trials_consumed"],1)

    def test_cancellation_after_cas_is_consuming_uncertain_final_zero(self):
        o=self.run_case(cas=True,outcome="skipped")
        self.assertEqual(o["status"],"FINAL_ZERO__START_INTENT_COMMITTED__START_OUTCOME_UNCERTAIN__NO_REPLAY")
        self.assertEqual(o["benchmark_trials_consumed"],1)
        self.assertEqual(o["consumed_final_failures_delta"],1)
        self.assertTrue(o["task_start_outcome_uncertain"])
        self.assertFalse(o["rerun_credit"])

if __name__=="__main__":
    unittest.main(verbosity=2)
