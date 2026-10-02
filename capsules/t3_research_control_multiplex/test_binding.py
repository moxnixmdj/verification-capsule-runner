from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"canonical"
EXPECTED={
  "canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json": "56520fac851048c3442209cb217beca2e56e86f4",
  "canonical/governance/ACTIVE_CONTRACT_PROOF_MODE_CLASSIFICATION_V1.json": "9bd8a3848510e1b450d07bcfd90ce6e6a9f4adbb",
  "canonical/governance/T3_UNKNOWN_DOMAIN_SCOPE_AUDIT_V1.json": "d3f05f1c0ed727c6e792cd3694461e92568770d7",
  "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "860cd929e3b7fdab6befec5bf052479dc4ae41ac",
  "canonical/verification/HLE_STRICT_LOWER_BOUND_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "624959a5c731b3ecff4cac200122d028744d15a3",
  "canonical/verification/HARBOR_ZERO_COST_TERMINAL_CARRIER_PREFLIGHT_20261002_V1.json": "608415d65b0b4cd50df9e3ca1044cd8f4eb7830f",
  "canonical/runtime/research_control_information_safe_candidate.py": "cd6bf6e4163bbba64878b856766b1af4372d68bc",
  "canonical/runtime/research_control_information_safe_proof.py": "16c47efee0e0e38f479163d1285d7079798efdaf",
  "canonical/runtime/hle_strict_reference_scorer.py": "d30882400982c058f1130b82af790b197767a091"
}

def blob(path: Path)->str:
    d=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def load(rel):
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise AssertionError(rel+" not object")
    return v

class T3ResearchMultiplexBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,sha in EXPECTED.items():
            self.assertEqual(blob(ROOT/rel),sha,rel)

    def test_binding_is_fail_closed_preterminal(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        self.assertEqual(b["behavior_id"],"ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001")
        self.assertEqual(b["proof_mode"],"PUBLIC_FIXED_BAR_MULTIPLEX_PLUS_DIRECT_BEHAVIOR_INSTRUMENTATION")
        self.assertFalse(b["execution_authority"])
        self.assertEqual(b["terminal_results_observed"],0)
        self.assertEqual(b["fresh_terminal_evidence_consumed"],0)
        self.assertEqual(b["capability_credit_delta"],0)
        self.assertEqual(b["family_credit_delta"],0)

    def test_public_bars_are_exact_and_do_not_require_paid_hle_judge(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        rows={x["id"]:x for x in b["public_surfaces"]}
        self.assertEqual(rows["HLE_WITH_TOOLS"]["target_percent"],67.7)
        self.assertFalse(rows["HLE_WITH_TOOLS"]["paid_judge_required"])
        self.assertEqual(rows["TERMINAL_BENCH_SCIENCE_0_1"]["target_percent"],58.7)
        self.assertEqual(rows["TERMINAL_BENCH_SCIENCE_0_1"]["route"],"PUBLIC_HARBOR_HARNESS")

    def test_candidate_information_boundary_is_clean(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        ib=b["information_boundary"]
        self.assertFalse(ib["candidate_receives_reference_answer"])
        self.assertFalse(ib["candidate_receives_hidden_oracle"])
        hidden=set(ib["hidden_from_candidate"])
        self.assertIn("REFERENCE_ANSWER",hidden)
        self.assertIn("HIDDEN_SOURCE_SUPPORT_TRUTH_BEFORE_FETCH",hidden)
        self.assertIn("POST_FREEZE_CASE_SELECTION_INFORMATION",hidden)

    def test_behavior_instrumentation_is_load_bearing(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        obs=set(b["direct_behavior_instrumentation"]["required_observables"])
        required={
          "QUERY_TARGETS_CURRENT_UNRESOLVED_MATERIAL_REQUIREMENT",
          "SOURCE_SELECTION_RESPECTS_FROZEN_AUTHORITY_AND_COST_RULE",
          "FAILED_FETCH_CAN_RECOVER_WITHOUT_REDUNDANT_SEARCH",
          "PROVENANCE_PRESERVED",
          "PREMATURE_STOP_REJECTED",
          "STOP_ONLY_AFTER_ALL_MATERIAL_REQUIREMENTS_SUPPORTED",
          "NO_REPEATED_RETRIEVAL_WITHOUT_NEW_REQUIREMENT_COVERAGE",
        }
        self.assertTrue(required.issubset(obs))
        self.assertTrue(b["terminal_acceptance"]["any_load_bearing_behavior_failure_blocks_contract_proof"])

    def test_no_cross_contract_inheritance(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        sep=set(b["uncovered_scope_audit"]["separate_contracts_not_inherited"])
        self.assertEqual(sep,{
          "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
          "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
          "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
        })

    def test_contamination_rules_are_frozen_false(self):
        b=load("canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json")
        self.assertTrue(all(v is False for v in b["contamination"].values()))

    def test_upstream_receipts_are_independent_passes(self):
        for rel in [
          "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
          "canonical/verification/HLE_STRICT_LOWER_BOUND_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
          "canonical/verification/HARBOR_ZERO_COST_TERMINAL_CARRIER_PREFLIGHT_20261002_V1.json",
        ]:
            r=load(rel)
            self.assertIn("PASS",str(r.get("status","")),rel)
            conclusion=r.get("workflow_conclusion")
            if conclusion is None and isinstance(r.get("public_verifier"),dict):
                conclusion=r["public_verifier"].get("conclusion")
            if conclusion is not None:
                self.assertEqual(conclusion,"success",rel)

    def test_classification_matches_binding(self):
        c=load("canonical/governance/ACTIVE_CONTRACT_PROOF_MODE_CLASSIFICATION_V1.json")
        rows=c.get("contracts") or c.get("classifications") or c.get("rows")
        self.assertIsInstance(rows,list)
        row=next(x for x in rows if x.get("behavior_id")=="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001")
        mode=str(row.get("mode") or row.get("proof_mode") or "")
        self.assertIn("PUBLIC",mode)
        self.assertIn("MULTIPLEX",mode)

if __name__=="__main__":
    unittest.main(verbosity=2)
