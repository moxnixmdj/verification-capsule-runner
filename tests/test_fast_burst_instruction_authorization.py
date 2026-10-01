import importlib.util, pathlib, sys, unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"session_bridge"))
spec=importlib.util.spec_from_file_location("fast",ROOT/"session_bridge/controller_fast.py")
fast=importlib.util.module_from_spec(spec); spec.loader.exec_module(fast)

class TestInstructionAuthorization(unittest.TestCase):
    def setUp(self):
        fast.CONFIG={"session_id":"s","lease_brain_commit":"a"*40}

    def good(self):
        return {
          "schema":"BRAIN_FAST_BURST_INSTRUCTION_AUTHORIZATION_V1",
          "session_id":"s",
          "lease_brain_commit":"a"*40,
          "canonical_frontier_commit":"b"*40,
          "canonical_frontier_status":"ALLOWS_INSTRUCTION_EXPOSURE",
          "freshness_revalidated":True,
          "instruction_exposure_authorized":True,
        }

    def test_good(self):
        self.assertIsNone(fast.instruction_authorization_blocker(self.good()))

    def test_lease_mismatch(self):
        p=self.good(); p["lease_brain_commit"]="c"*40
        self.assertEqual(fast.instruction_authorization_blocker(p),"LEASE_COMMIT_MISMATCH")

    def test_frontier_denial(self):
        p=self.good(); p["canonical_frontier_status"]="BLOCKED"
        self.assertEqual(fast.instruction_authorization_blocker(p),"CANONICAL_FRONTIER_DOES_NOT_ALLOW_EXPOSURE")

    def test_freshness_required(self):
        p=self.good(); p["freshness_revalidated"]=False
        self.assertEqual(fast.instruction_authorization_blocker(p),"FRESHNESS_NOT_REVALIDATED")

    def test_missing_lease_in_session_fails_closed(self):
        fast.CONFIG={"session_id":"s"}
        self.assertEqual(fast.instruction_authorization_blocker(self.good()),"SESSION_LEASE_BRAIN_COMMIT_MISSING")

if __name__=="__main__":
    unittest.main()
