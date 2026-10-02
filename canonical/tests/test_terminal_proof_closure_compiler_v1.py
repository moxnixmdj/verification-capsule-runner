import json, unittest
from canonical.runtime.terminal_proof_closure_compiler_v1 import compile_frontier, self_test
class CompilerTests(unittest.TestCase):
    def test_self_test(self): self_test()
    def test_current_frontier(self):
        with open("canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json",encoding="utf-8") as f: basis=json.load(f)
        with open("canonical/governance/TERMINAL_PROOF_EVIDENCE_INDEX_V1.json",encoding="utf-8") as f: idx=json.load(f)
        out=compile_frontier(basis,idx)
        self.assertEqual(out["errors"],[])
        self.assertEqual(out["active_contract_count"],12)
        self.assertEqual(out["terminal_ready"],["SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001","TASK_TO_DELEGATION_GRAPH_001"])
        self.assertEqual(out["mechanical_closure_candidates"],[])
        by={x["behavior_id"]:x for x in out["contracts"]}
        self.assertEqual(by["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"]["compile_state"],"SEMANTIC_RESIDUAL")
        self.assertIn("BASIS::DYNAMIC_TOOL_DISCOVERY_BEYOND_PREENUMERATED_CATALOG_NOT_YET_PROVEN",by["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"]["semantic_residuals"])
        self.assertFalse(out["execution_authority"])
if __name__=="__main__": unittest.main(verbosity=2)
