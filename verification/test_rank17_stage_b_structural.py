import copy, hashlib, json, shutil, tempfile, unittest
from pathlib import Path

from canonical.runtime.data_anonymization_stage_b_gate import evaluate

FILES = [
 "canonical/runtime/data_anonymization_stage_b_gate.py",
 "canonical/runtime/requirement_graph_kernel.py",
 "canonical/runtime/independent_acceptance_model.py",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_CONTRACT_V1.json",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_SOURCE_ACCOUNTING_V1.json",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json",
]

def materialize(dst: Path):
    root=Path(".")
    for rel in FILES:
        src=root/rel
        out=dst/rel
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,out)

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()

EXPECTED_BLOBS = {
 "canonical/runtime/data_anonymization_stage_b_gate.py":"c50145ae45d17a4d4b00bd3b20552362d42c52ef",
 "canonical/runtime/requirement_graph_kernel.py":"18001b4b7ace6fe77497c7fb92dd8d9dd2d0f607",
 "canonical/runtime/independent_acceptance_model.py":"c420b8be1f79a0b06afa98f461f443f53d7fc77a",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_CONTRACT_V1.json":"fbb8d0d8cec3c2a460af57791dcb64415b5ffb1e",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_SOURCE_ACCOUNTING_V1.json":"adf68f40b2a923584db5fe7a32942b684d132c42",
 "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json":"9b5e093954df99f36b305220f50955eadaa1712b",
}

class Rank17StageB(unittest.TestCase):
    def test_exact_brain_blobs_are_mirrored(self):
        for rel, expected in EXPECTED_BLOBS.items():
            self.assertEqual(git_blob_sha(Path(rel)), expected, rel)
    def test_exact_frozen_contract_passes_structural_gate(self):
        out=evaluate(Path("."))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["requirement_count"],20)
        self.assertEqual(out["requirement_mutants_survived"],0)
        self.assertEqual(out["verifier_mutants_survived"],[])
        self.assertFalse(out["task_execution_authorized_by_this_gate"])

    def test_hidden_verifier_exposure_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); materialize(root)
            p=root/"canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json"
            x=json.loads(p.read_text()); x["hidden_verifier_read"]=True
            p.write_text(json.dumps(x))
            out=evaluate(root)
            self.assertFalse(out["pass"])
            self.assertIn("LEDGER_HIDDEN_EXPOSURE",out["failed_predicates"])

    def test_removed_failure_mode_coverage_is_killed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); materialize(root)
            p=root/"canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_CONTRACT_V1.json"
            x=json.loads(p.read_text())
            for chk in x["independent_acceptance_model"]["checks"]:
                chk["detects"]=[m for m in chk.get("detects",[]) if m!="ignore_effective_date"]
            p.write_text(json.dumps(x))
            out=evaluate(root)
            self.assertFalse(out["pass"])
            self.assertTrue(any("VERIFIER_MUTATION_SURVIVORS" in s or s=="INDEPENDENT_ACCEPTANCE"
                                for s in out["failed_predicates"]))

    def test_weakened_memory_design_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); materialize(root)
            p=root/"canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_STAGE_B_CONTRACT_V1.json"
            x=json.loads(p.read_text())
            x["feasibility"]["memory_design"]=["load everything into memory"]
            p.write_text(json.dumps(x))
            out=evaluate(root)
            self.assertFalse(out["pass"])
            self.assertTrue(any(s.startswith("FEASIBILITY_MISSING:") for s in out["failed_predicates"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
