from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.terminal_prequalification_reducer import evaluate


class LiveTerminalAuthorityDerivationTests(unittest.TestCase):
    def test_live_12_contract_state_derives_authority_without_self_assertion(self):
        out = evaluate(Path("."))
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["execution_authority"], out)
        self.assertEqual(out["authorization"], "T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE")
        self.assertEqual(out["failed_predicates"], [])
        self.assertEqual(
            out["authority_derivation"],
            "PURE_FUNCTION_OF_ACTIVE_CONTRACT_COVERAGE_ROUTE_ADMISSIBILITY_PROTOCOL_SET_AND_EXPLICIT_PREWAVE_FACTS",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
