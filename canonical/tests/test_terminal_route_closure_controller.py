from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_route_closure_controller import evaluate


class TerminalRouteClosureControllerTests(unittest.TestCase):
    def run_basis(self, contracts, declared_closed=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/governance"
            p.mkdir(parents=True)
            closed = sum(
                x.get("proof_state") == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE"
                for x in contracts
            )
            (p / "ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(
                json.dumps({
                    "active_contract_count": len(contracts),
                    "admissible_frozen_terminal_route_count": (
                        closed if declared_closed is None else declared_closed
                    ),
                    "contracts": contracts,
                }),
                encoding="utf-8",
            )
            return evaluate(root)

    def test_closed_routes_are_removed_from_queue(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE",
                "blockers": [],
            },
            {
                "behavior_id": "B",
                "portfolio": "T2",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
        ])
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["closed_route_count"], 1)
        self.assertEqual([x["behavior_id"] for x in out["queue"]], ["B"])

    def test_binding_only_precedes_scope_expansion(self):
        out = self.run_basis([
            {
                "behavior_id": "BIND",
                "portfolio": "T2",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
            {
                "behavior_id": "EXPAND",
                "portfolio": "T0_T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "WHOLE_CONTRACT_SCOPE_EQUIVALENCE_NOT_YET_PROVEN",
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                ],
            },
        ])
        self.assertEqual(out["queue"][0]["behavior_id"], "BIND")

    def test_multiportfolio_leverage_breaks_equal_cost_tie(self):
        out = self.run_basis([
            {
                "behavior_id": "ONE",
                "portfolio": "T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
            {
                "behavior_id": "FOUR",
                "portfolio": "T0_T1_T2_T3",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
        ])
        self.assertEqual(out["queue"][0]["behavior_id"], "FOUR")

    def test_declared_closed_count_cannot_drift(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE",
                "blockers": [],
            },
        ], declared_closed=0)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ADMISSIBLE_ROUTE_COUNT_MISMATCH", out["errors"])

    def test_open_route_without_blocker_fails_closed(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "ROUTE_REQUIRED",
                "blockers": [],
            },
        ])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OPEN_ROUTE_WITHOUT_BLOCKER:A", out["errors"])


    def test_external_comparator_block_is_classified_and_not_scope_expansion(self):
        out = self.run_basis([
            {
                "behavior_id": "TRAJECTORY",
                "portfolio": "T0_T2",
                "proof_state": "BOUNDED_INFORMATION_SAFE_PREFLIGHT_PRESERVED__OPEN_DOMAIN_MATCHED_TERMINAL_PROTOCOL_FREEZE_PENDING",
                "blockers": [
                    "FREEZE_SELF_VERIFICATION_CAUSAL_INTERVENTION_CHALLENGE_SOURCE_POOL_AND_SCORER",
                    "FREEZE_MATCHED_HARNESS_INFORMATION_TOOL_RESOURCE_AND_AUTHORITY_SYMMETRY",
                    "EXACT_OPUS_5_5_CASE_LEVEL_COMPARATOR_UNAVAILABLE_AT_ZERO_INCREMENTAL_SPEND_FOR_UNCOVERED_CAUSAL_RECOVERY_SCOPE",
                ],
            },
        ])
        self.assertEqual(out["status"], "PASS")
        row = out["queue"][0]
        self.assertEqual(row["blocker_classes"]["external_block"], 1)
        self.assertEqual(row["blocker_classes"]["open_domain_protocol"], 2)
        self.assertEqual(row["blocker_classes"]["scope_expansion"], 0)
        self.assertEqual(
            row["next_action_class"],
            "EXTERNAL_BLOCKED__FREEZE_INTERNAL_PROTOCOL_FIELDS_ONLY__DO_NOT_SPEND_CLEAN_CASES",
        )

    def test_external_blocked_lane_is_ranked_after_actionable_internal_lane(self):
        out = self.run_basis([
            {
                "behavior_id": "ACTIONABLE",
                "portfolio": "T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
            {
                "behavior_id": "BLOCKED",
                "portfolio": "T0_T2",
                "proof_state": "BOUNDED_INFORMATION_SAFE_PREFLIGHT_PRESERVED",
                "blockers": [
                    "FREEZE_MATCHED_HARNESS_INFORMATION_TOOL_RESOURCE_AND_AUTHORITY_SYMMETRY",
                    "EXACT_OPUS_5_5_CASE_LEVEL_COMPARATOR_UNAVAILABLE_AT_ZERO_INCREMENTAL_SPEND",
                ],
            },
        ])
        self.assertEqual(
            [x["behavior_id"] for x in out["queue"]],
            ["ACTIONABLE", "BLOCKED"],
        )

if __name__ == "__main__":
    unittest.main()


class TerminalRouteEvidenceFreshnessIntegrationTests(unittest.TestCase):
    def test_changed_candidate_is_scheduled_for_exact_reverification(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); gov=root/"canonical/governance"; rt=root/"canonical/runtime"; ver=root/"canonical/verification"
            gov.mkdir(parents=True); rt.mkdir(parents=True); ver.mkdir(parents=True)
            candidate=rt/"candidate.py"; candidate.write_text("NEW=1\n",encoding="utf-8")
            old=b"OLD=1\n"; old_sha=hashlib.sha1(b"blob "+str(len(old)).encode()+b"\0"+old).hexdigest()
            (ver/"receipt.json").write_text(json.dumps({"status":"INDEPENDENT_PASS","exact_brain_blobs":{"canonical/runtime/candidate.py":old_sha}}),encoding="utf-8")
            (gov/"ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(json.dumps({"active_contract_count":1,"admissible_frozen_terminal_route_count":0,"contracts":[{"behavior_id":"X","portfolio":"T1","proof_state":"INDEPENDENT_PREFLIGHT_PASS","blockers":["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],"candidate":"canonical/runtime/candidate.py","independent_preflight":"canonical/verification/receipt.json"}]}),encoding="utf-8")
            out=evaluate(root); row=out["queue"][0]
            self.assertEqual(row["blocker_classes"]["stale_evidence"],1)
            self.assertEqual(row["next_action_class"],"REVERIFY_CHANGED_BYTES_BEFORE_ANY_SCOPE_OR_ACCEPTANCE_PROMOTION")
            self.assertTrue(row["evidence_freshness"]["stale"])

    def test_acceptance_proof_has_specific_action(self):
        out=self.run_basis([{"behavior_id":"X","portfolio":"T2","proof_state":"PENDING","blockers":["REGISTRY_TERMINAL_ACCEPTANCE_PROOF_NOT_YET_TRUTHFULLY_ESTABLISHED"]}])
        self.assertEqual(out["queue"][0]["blocker_classes"]["acceptance_proof"],1)
        self.assertEqual(out["queue"][0]["next_action_class"],"ESTABLISH_REGISTERED_TERMINAL_ACCEPTANCE_PROOF")

if __name__=="__main__": unittest.main()
