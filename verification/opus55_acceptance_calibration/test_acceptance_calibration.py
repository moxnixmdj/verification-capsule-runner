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


if __name__=="__main__":
    unittest.main(verbosity=2)
