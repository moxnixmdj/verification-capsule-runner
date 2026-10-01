import copy, json, shutil, tempfile, unittest
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

class Rank17StageB(unittest.TestCase):
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
