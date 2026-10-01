import copy,json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from prequalification_stage_a_generic_rank23_exact import evaluate

TASK="layout-config-recreation2"
RANK=23
IDENTITY="78fe5d2840c1f1fb25a59693fc0bfe2676d10f07e1c66c0bcd03c90a8fc71aad"
LEDGER="canonical/capabilities/opus55/LAYOUT_CONFIG_RECREATION2_RANK23_CONTAMINATION_LEDGER_V1.json"

class Rank23ExactStageA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot=json.loads((Path(__file__).parent/"rank23_stage_a_exact_snapshot.json").read_text())
        cls.files={p:v["content"] for p,v in cls.snapshot["brain_files"].items()}
        cls.ledger=cls.files[LEDGER]

    def evaluate_files(self, files):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for p,obj in files.items():
                q=root/p
                q.parent.mkdir(parents=True,exist_ok=True)
                q.write_text(json.dumps(obj),encoding="utf-8")
            return evaluate(root,LEDGER,TASK,RANK,IDENTITY)

    def test_exact_current_snapshot_passes_stage_a_only(self):
        out=self.evaluate_files(copy.deepcopy(self.files))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["authorization"],"STAGE_B_INSTRUCTION_EXPOSURE_ONLY")
        self.assertFalse(out["task_execution_authorized"])

    def test_instruction_read_fails_closed(self):
        f=copy.deepcopy(self.files); f[LEDGER]["instruction_read"]=True
        self.assertFalse(self.evaluate_files(f)["pass"])

    def test_external_search_fails_closed(self):
        f=copy.deepcopy(self.files); f[LEDGER]["task_specific_web_or_repo_search"]=True
        self.assertFalse(self.evaluate_files(f)["pass"])

    def test_unclassified_extra_hit_fails_closed(self):
        f=copy.deepcopy(self.files); f[LEDGER]["prior_exposure_search"]["brain_pr_hits"]+=1
        out=self.evaluate_files(f)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE",out["failed_predicates"])

    def test_disqualifying_hit_fails_closed(self):
        f=copy.deepcopy(self.files)
        f[LEDGER]["prior_exposure_search"]["runner_code_hits"]=1
        f[LEDGER]["prior_exposure_search"]["disqualifying_hits"]["runner_code_hits"]=1
        out=self.evaluate_files(f)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_DISQUALIFYING_HIT",out["failed_predicates"])

    def test_incomplete_stage_a_policy_fails_closed(self):
        f=copy.deepcopy(self.files)
        req=f["canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"]["staged_admission"]["stage_a_pre_exposure"]["required"]
        req.remove("NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS")
        out=self.evaluate_files(f)
        self.assertFalse(out["pass"])
        self.assertIn("STAGE_A_POLICY_INCOMPLETE",out["failed_predicates"])

if __name__=="__main__":
    unittest.main(verbosity=2)
