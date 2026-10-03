import json
import unittest
from copy import deepcopy
from pathlib import Path

from opus55_acceptance_calibration_reducer_v1 import evaluate


def load(name):
    return json.loads(Path(name).read_text(encoding="utf-8"))


class AcceptanceCalibrationTests(unittest.TestCase):
    def test_exact_frozen_inputs_derive_2_closed_17_open(self):
        out=evaluate(
            load("OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"),
            load("OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            load("TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["target_family_count"],19,out)
        self.assertEqual(out["behavioral_pass_family_count"],19,out)
        self.assertEqual(out["acceptance_calibrated_family_count"],2,out)
        self.assertEqual(out["acceptance_pending_family_count"],17,out)
        self.assertEqual(
            out["acceptance_calibrated_families"],
            ["EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"],
        )

    def synthetic_fixture(self):
        envelope={"families":[{"id":f"F{i}"} for i in range(19)]}
        protocols={"protocols":[{"family":f"F{i}","proof_mode":"X","status":"PASS"} for i in range(19)]}
        reduction={"family_verdict":{"valid":True,"passed_families":[f"F{i}" for i in range(19)]}}
        return envelope,protocols,reduction

    def test_all_protocols_pass_is_terminal_acceptance_pass(self):
        out=evaluate(*self.synthetic_fixture())
        self.assertTrue(out["pass"],out)

    def test_behavioral_pass_cannot_override_open_protocol(self):
        args=list(self.synthetic_fixture())
        args[1]["protocols"][3]["status"]="DEFINED_RESULT_OPEN"
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("F3",out["acceptance_pending_families"])

    def test_missing_behavioral_pass_fails_closed(self):
        args=list(self.synthetic_fixture())
        args[2]["family_verdict"]["passed_families"].remove("F7")
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("F7",out["behavioral_missing_families"])

    def test_protocol_family_set_mismatch_fails_closed(self):
        args=list(self.synthetic_fixture())
        args[1]["protocols"].pop()
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("PROTOCOL_FAMILY_SET_MISMATCH",out["errors"])


import hashlib

RECOVERY_PROMOTION_HEAD="efa03276ecb5232ca4d2ce9b66ea60ab637a82a1"
RECOVERY_PROMOTION_BLOBS={
    "canonical/CANONICAL_POINTER.json":"af4e6b52b013f8106b15085d696ab2b1da81ad43",
    "canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json":"1b7833c2c0c3bec26d1e22cb20b96e2962c99cf1",
    "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json":"81813f023ae166ae33d3c7d660315e5cd44712d5",
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"40690a3f2e1cd5a0f7d90d0564efc4383b8bdbdd",
    "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json":"76a34f1a5ec60c9a6f0de4eb6c9805f6e6291a28",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"d39164cc78174b34174cece115728cf0e657aed6",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"e62c732937d4dae4eb5297dff96d354dcc52236e",
    "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":"7a72f37a0e24329c8c55eef22b69151638f93327",
    "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json":"5a510bacad38139206d602c91111aa649ff03f07",
    "canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"48a865f38f65be212df1cf0ba52d296b71cd003a",
}
MIRROR_ROOT=Path(__file__).resolve().parent/"recovery_promotion_v3"

def _git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _local(path:str)->Path:
    return MIRROR_ROOT/path.replace("/","__")

def _load_exact(path:str):
    p=_local(path)
    data=p.read_bytes()
    actual=_git_blob_sha(data)
    expected=RECOVERY_PROMOTION_BLOBS[path]
    if actual!=expected:
        raise AssertionError((path,expected,actual,str(p)))
    return json.loads(data.decode("utf-8"))

class RecoveryFinalPromotionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs={p:_load_exact(p) for p in RECOVERY_PROMOTION_BLOBS}

    def test_all_load_bearing_exact_blobs_bound(self):
        self.assertEqual(len(self.docs),10)

    def test_integrator_receipt_is_exact_and_recovery_only(self):
        r=self.docs["canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
        self.assertEqual(r["status"],"INDEPENDENT_PUBLIC_RUNNER_PASS__RECOVERY_ONLY_ACCEPTANCE_DELTA_8_TO_11_ATOMIC__3_TO_4_FAMILIES__ZERO_REALITY__ZERO_CREDIT_FROM_VERIFIER")
        self.assertTrue(r["verified_result"]["recovery_only_delta"])
        self.assertEqual(r["verified_result"]["before"],{"proved_atomic":8,"unresolved_atomic":30,"accepted_families":3,"open_families":16})
        self.assertEqual(r["verified_result"]["after"],{"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15})
        self.assertEqual(r["new_reality_units_consumed"],0)
        self.assertEqual(r["terminal_results_replayed"],0)

    def test_atomic_ledger_is_exact_recovery_only_delta(self):
        ledger=self.docs["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]
        self.assertEqual(ledger["saturation"]["proved_predicate_count"],11)
        self.assertEqual(ledger["saturation"]["unresolved_predicate_count"],27)
        self.assertEqual(ledger["saturation"]["receipt"],"canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        ids={
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        }
        rows={x["predicate_id"]:x for x in ledger["claims"] if x.get("predicate_id") in ids}
        self.assertEqual(set(rows),ids)
        for row in rows.values():
            self.assertEqual(row["state"],"PROVED")
            self.assertTrue(row["scope_complete"])
            self.assertEqual(row["source_path"],"canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
            self.assertEqual(row["source_sha"],"48a865f38f65be212df1cf0ba52d296b71cd003a")

    def test_all_canonical_acceptance_projections_agree(self):
        auth=self.docs["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
        self.assertEqual(auth["truth"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(auth["atomic_acceptance_frontier"]["proved"],11)
        self.assertEqual(auth["atomic_acceptance_frontier"]["unresolved"],27)
        self.assertFalse(auth["truth"]["achieved"])
        self.assertIn("RECOMPUTE_RECEIPT_DERIVED_27_PREDICATE",auth["next"])
        self.assertFalse(bool(auth["atomic_acceptance_frontier"].get("authorized_acceptance_case_actions")))

        manifest=self.docs["canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"]
        self.assertEqual(manifest["behavioral_pass_family_count"],19)
        self.assertEqual(manifest["behavioral_quarantined_family_count"],0)
        summary=manifest["opus55_acceptance_summary"]
        self.assertEqual(summary["calibrated_family_count"],4)
        self.assertEqual(summary["pending_family_count"],15)
        self.assertEqual(summary["atomic_predicates"],{"proved":11,"unresolved":27,"total":38})
        rec=next(x for x in manifest["families"] if x["id"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertEqual(rec["opus55_acceptance_state"],"PASS")

        matrix=self.docs["canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"]
        self.assertEqual(matrix["postwave_acceptance_summary"]["calibrated_family_count"],4)
        self.assertEqual(matrix["postwave_acceptance_summary"]["verified_owned_family_count"],2)
        recm=next(x for x in matrix["rows"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertIn("PASS_VIA_SCOPE_COMPLETE_ZERO_REALITY_STRONGER_PROOF",recm["postwave_opus55_acceptance_status"])
        self.assertTrue(str(recm["postwave_ownership_credit"]).startswith("ZERO_"))

        frontier=self.docs["canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json"]
        self.assertEqual(frontier["acceptance_truth"]["accepted_families"],4)
        self.assertEqual(frontier["acceptance_truth"]["proved_atomic_predicates"],11)
        self.assertEqual(frontier["acceptance_truth"]["unresolved_atomic_predicates"],27)
        self.assertFalse(frontier["acceptance_truth"]["achieved"])

        scoreboard=self.docs["canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"]
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["accepted_families"],4)
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["proved_atomic_predicates"],11)
        hierarchy=self.docs["canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"]
        self.assertIn("4_OF_19",hierarchy["probe_state"])
        pointer=self.docs["canonical/CANONICAL_POINTER.json"]
        self.assertIn("15_OF_19",pointer["current_frontier"]["critical_blocker"])
        queue=self.docs["canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json"]
        self.assertIn("27_OF_38",queue["exact_blocker"])
        self.assertIn("27_PREDICATE",queue["next_action"])

    def test_zero_reality_no_ownership_overclaim_and_fresh_reality_stays_closed(self):
        auth=self.docs["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
        self.assertFalse(auth["truth"]["achieved"])
        self.assertIn("NO_FRESH_REALITY",auth["next"])
        matrix=self.docs["canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"]
        self.assertEqual(len(matrix["summary"]["verified_owned_equal_or_better_capabilities"]),2)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",matrix["summary"]["owned_components_not_full_family"])

if __name__=="__main__":
    unittest.main(verbosity=2)
