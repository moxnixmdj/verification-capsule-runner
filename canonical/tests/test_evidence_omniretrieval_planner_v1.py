from __future__ import annotations
import unittest
from canonical.runtime.evidence_omniretrieval_planner_v1 import ProofObligation, compile_channels, saturation_verdict

class Tests(unittest.TestCase):
    def test_nonenglish_alias_and_invariants_survive(self):
        p=compile_channels(ProofObligation(
            obligation_id="X",
            concepts=("tool discovery",),
            aliases=("工具发现","ツール発見"),
            numeric_anchors=("77.8%","0.778"),
            identifiers=("toolathlon","benchmark@0.1.0"),
            code_symbols=("evaluate_tools","ToolCall"),
            hashes=("abc123def456",),
            seed_repositories=("org/repo",),
        ))
        self.assertEqual(p["status"],"COMPILED")
        self.assertIn("工具发现",p["channels"]["MULTILINGUAL_SEED"])
        self.assertIn("0.778",p["channels"]["INVARIANT"])
        self.assertTrue(p["channels"]["STRUCTURAL_CODE"])
        self.assertTrue(p["channels"]["HISTORY"])
        self.assertTrue(p["channels"]["GRAPH"])

    def test_lexical_only_fails_closed(self):
        p=compile_channels(ProofObligation(obligation_id="X", concepts=("only words",)))
        self.assertEqual(p["status"],"FAIL_CLOSED")

    def test_saturation_requires_every_active_channel(self):
        p=compile_channels(ProofObligation(
            obligation_id="X", concepts=("x",), identifiers=("id-x",), seed_repositories=("o/r",)
        ))
        rounds=[]
        for c in p["active_channels"]:
            rounds += [{"channel":c,"new_acceptance_relevant_artifacts":0} for _ in range(2)]
        v=saturation_verdict(p,rounds)
        self.assertEqual(v["status"],"ACCESSIBLE_SOURCE_FIXED_POINT")
        self.assertFalse(v["claims_all_information_in_existense"])

    def test_new_artifact_breaks_saturation(self):
        p=compile_channels(ProofObligation(
            obligation_id="X", concepts=("x",), identifiers=("id-x",), seed_repositories=("o/r",)
        ))
        rounds=[]
        for c in p["active_channels"]:
            rounds += [{"channel":c,"new_acceptance_relevant_artifacts":0} for _ in range(2)]
        rounds += [{"channel":"INVARIANT","new_acceptance_relevant_artifacts":1}]
        v=saturation_verdict(p,rounds)
        self.assertEqual(v["status"],"OPEN")
        self.assertIn("INVARIANT",v["unsaturated_channels"])

if __name__=="__main__":
    unittest.main(verbosity=2)
