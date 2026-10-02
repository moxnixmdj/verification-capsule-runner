from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.proof_route_dominance import evaluate

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V4.json"

class GlobalSurfaceDominanceV4Tests(unittest.TestCase):
    def test_v4_has_no_uncovered_obligations(self):
        payload=json.loads(INPUT.read_text(encoding="utf-8"))
        out=evaluate(payload)
        self.assertEqual(out["status"],"COMPLETE",out)
        self.assertEqual(out["global_uncovered_obligations"],[],out)
        self.assertIn("COMPOSED_RAW_SOURCE_TO_ACCEPTANCE_TERMINAL_PROOF",out["admissible_routes"])
        for row in out["blocked_route_verdicts"]:
            self.assertTrue(row["redundant"],row)

    def test_raw_source_acceptance_scope_is_explicit(self):
        payload=json.loads(INPUT.read_text(encoding="utf-8"))
        route=next(r for r in payload["routes"] if r["id"]=="COMPOSED_RAW_SOURCE_TO_ACCEPTANCE_TERMINAL_PROOF")
        self.assertIn("canonical/governance/M0A_COMPLETE_ACTION_BUNDLE_V2.json",route["evidence"])
        self.assertIn("canonical/runtime/source_contract_compiler.py",route["evidence"])
        self.assertIn("canonical/runtime/requirement_acceptance_compiler.py",route["evidence"])
        self.assertIn("MATCHED_OPUS_LEVEL_SEMANTIC_ACCEPTANCE_OR_STRONGER_INDEPENDENT_GOLD",route["acceptance"])
        self.assertIn("REQUIREMENT_ACCEPTANCE_COMPILER_ALONE_DOES_NOT_COVER_RAW_SOURCE_SEMANTICS",route["nonclaim"])

if __name__=="__main__":
    unittest.main()
