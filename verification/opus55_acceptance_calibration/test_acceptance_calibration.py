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

RECOVERY_CURRENT_HEAD="08190d4b7ac0127d3ef21a9715b3e6e8199ada08"
RECOVERY_CURRENT_AUTHORITY_COMMIT="ae94a6390b05dc3dea7deecbee691093d62bdde2"
RECOVERY_CURRENT_BLOBS={
    "canonical/CANONICAL_POINTER.json":"01dac2387d8c1a4f904f83386c20f06c3c5bf1b7",
    "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json":"14ae8d5bcfdc8413853df084cbf0cec729df40f0",
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"3cbbcd1ddabde7dbf4c3f4d118bdb9d78d0c8605",
    "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json":"f45e724f11b65f9a8ec3931b6f5eb1c87ec7c558",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"2560dbf990a4f39f006884a2c0d1fa7950e15795",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
    "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":"53213e9af653606925f1c800f986cb7b9e396a66",
    "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json":"dc629d69b1bbf1ebf25e99c474588ad0aa76fb92",
    "canonical/tests/test_recovery_acceptance_promotion_v2.py":"967ce9cb723805ece8f6bd66dad8e8e8c45f9e31",
    "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json":"981c8ac9b66ee7fccf5b531525849e29df9be483",
}
RECOVERY_CURRENT_ROOT=Path("recovery_promotion_current")

def _recovery_current_bytes(path):
    return (RECOVERY_CURRENT_ROOT/path.replace("/","__")).read_bytes()

def _recovery_current_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()

def _recovery_current_json(path):
    data=_recovery_current_bytes(path)
    actual=_recovery_current_blob_sha(data)
    expected=RECOVERY_CURRENT_BLOBS[path]
    if actual!=expected:
        raise AssertionError((path,expected,actual))
    return json.loads(data.decode("utf-8"))

class RecoveryCurrentFinalPromotionTests(unittest.TestCase):
    def test_exact_current_pr1308_blob_identities(self):
        self.assertEqual(len(RECOVERY_CURRENT_BLOBS),10)
        for path,expected in RECOVERY_CURRENT_BLOBS.items():
            self.assertEqual(_recovery_current_blob_sha(_recovery_current_bytes(path)),expected,path)

    def test_recovery_only_atomic_delta_is_11_of_38(self):
        ledger=_recovery_current_json("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        self.assertEqual(ledger["saturation"]["proved_predicate_count"],11)
        self.assertEqual(ledger["saturation"]["unresolved_predicate_count"],27)
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
            self.assertEqual(row["source_sha"],"981c8ac9b66ee7fccf5b531525849e29df9be483")

    def test_all_current_projections_agree_and_remain_terminal_false(self):
        auth=_recovery_current_json("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        self.assertEqual(auth["truth"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(auth["atomic_acceptance_frontier"]["proved"],11)
        self.assertEqual(auth["atomic_acceptance_frontier"]["unresolved"],27)
        self.assertFalse(auth["truth"]["achieved"])
        self.assertEqual(auth["atomic_acceptance_frontier"]["authorized_acceptance_case_actions"],[])
        self.assertIn("RECOMPUTE_LIVE_27_PREDICATE",auth["next"])

        manifest=_recovery_current_json("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
        summary=manifest["opus55_acceptance_summary"]
        self.assertEqual(summary["calibrated_family_count"],4)
        self.assertEqual(summary["pending_family_count"],15)
        self.assertEqual(summary["atomic_predicates"],{"proved":11,"unresolved":27,"total":38})

        matrix=_recovery_current_json("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
        self.assertEqual(matrix["postwave_acceptance_summary"]["calibrated_family_count"],4)
        self.assertEqual(matrix["postwave_acceptance_summary"]["verified_owned_family_count"],2)

        frontier=_recovery_current_json("canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json")
        self.assertEqual(frontier["acceptance_truth"]["accepted_families"],4)
        self.assertEqual(frontier["acceptance_truth"]["proved_atomic_predicates"],11)
        self.assertEqual(frontier["acceptance_truth"]["unresolved_atomic_predicates"],27)

        scoreboard=_recovery_current_json("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["accepted_families"],4)
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["proved_atomic_predicates"],11)

        hierarchy=_recovery_current_json("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
        self.assertIn("4_OF_19",hierarchy["probe_state"])

        pointer=_recovery_current_json("canonical/CANONICAL_POINTER.json")
        self.assertIn("15_OF_19",pointer["current_frontier"]["critical_blocker"])
        self.assertEqual(
            pointer["current_frontier"]["terminal_authority_projection"]["source_commit_sha"],
            RECOVERY_CURRENT_AUTHORITY_COMMIT,
        )

    def test_zero_new_reality_and_no_ownership_overclaim(self):
        receipt=_recovery_current_json("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json")
        self.assertEqual(receipt["new_reality_units_consumed"],0)
        self.assertEqual(receipt["terminal_results_replayed"],0)
        self.assertTrue(receipt["verified"]["scope_complete"])
        self.assertEqual(receipt["verified"]["proposed_atomic_acceptance_delta"],3)
        matrix=_recovery_current_json("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
        self.assertEqual(len(matrix["summary"]["verified_owned_equal_or_better_capabilities"]),2)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",matrix["summary"]["owned_components_not_full_family"])


if __name__=="__main__":
    unittest.main(verbosity=2)
