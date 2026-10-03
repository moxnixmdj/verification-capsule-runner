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
import urllib.request

RECOVERY_PROMOTION_HEAD="6f42aa5df3980dd0831b272ec10cb2c4024186af"
RECOVERY_PROMOTION_BLOBS={
    "canonical/CANONICAL_POINTER.json":"faa99b3f84a0bd52fe577ec0f789238982c6e93b",
    "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json":"00a2914dd7f28c872c885cb04a2cf8cd49be1d83",
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"3cbbcd1ddabde7dbf4c3f4d118bdb9d78d0c8605",
    "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json":"89b6870b037e095a1620f3737538b19481898e5e",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"97af7916b35bdd678f4afbcc2507b35f7d66a512",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
    "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":"93fc43d1e60813cb362360821d1ad43880b0af45",
    "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json":"dc629d69b1bbf1ebf25e99c474588ad0aa76fb92",
    "canonical/tests/test_recovery_acceptance_promotion_v2.py":"967ce9cb723805ece8f6bd66dad8e8e8c45f9e31",
    "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json":"981c8ac9b66ee7fccf5b531525849e29df9be483",
}

def _git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()

def _fetch_brain(path:str):
    url=f"https://raw.githubusercontent.com/moxnixmdj/brain/{RECOVERY_PROMOTION_HEAD}/{path}"
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-RecoveryPromotionVerifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        data=r.read()
    expected=RECOVERY_PROMOTION_BLOBS[path]
    actual=_git_blob_sha(data)
    if actual!=expected:
        raise AssertionError((path,expected,actual))
    if path.endswith(".json"):
        return json.loads(data.decode("utf-8"))
    return data.decode("utf-8")

class RecoveryFinalPromotionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs={p:_fetch_brain(p) for p in RECOVERY_PROMOTION_BLOBS}

    def test_all_exact_pr1306_blobs_bound(self):
        self.assertEqual(len(self.docs),10)

    def test_atomic_ledger_is_recovery_only_11_of_38(self):
        ledger=self.docs["canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"]
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
            self.assertEqual(
                row["source_path"],
                "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",
            )
            self.assertEqual(row["source_sha"],"981c8ac9b66ee7fccf5b531525849e29df9be483")

    def test_all_canonical_projections_agree_4_of_19_11_of_38(self):
        auth=self.docs["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]
        self.assertEqual(auth["truth"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(auth["atomic_acceptance_frontier"]["proved"],11)
        self.assertEqual(auth["atomic_acceptance_frontier"]["unresolved"],27)
        self.assertFalse(auth["truth"]["achieved"])

        manifest=self.docs["canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"]
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
        self.assertIn("PASS_VIA_SCOPE_COMPLETE_STRONGER_PROOF",recm["postwave_opus55_acceptance_status"])

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

    def test_zero_reality_and_no_whole_ownership_overclaim(self):
        receipt=self.docs["canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"]
        self.assertEqual(receipt["new_reality_units_consumed"],0)
        self.assertEqual(receipt["terminal_results_replayed"],0)
        matrix=self.docs["canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"]
        self.assertEqual(len(matrix["summary"]["verified_owned_equal_or_better_capabilities"]),2)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",matrix["summary"]["owned_components_not_full_family"])

if __name__=="__main__":
    unittest.main(verbosity=2)
