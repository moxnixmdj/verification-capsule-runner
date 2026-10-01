import json, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from prequalification_stage_a_generic import evaluate

REF="452bf305c6daa62fc59061d22133a7cbc7c1572e"
TASK="data-anonymization"; RANK=17
HASH="65c02927e5914f433922f83db07e89608b906e383c6bed904f452640238bd31c"
LEDGER="canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json"

def deps():
    return {
      "canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json":{"status":"FROZEN_X","benchmark_ref":REF,"stage1_target_success_fraction":0.664,"target_model":"Claude Opus 5.5"},
      "canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json":{"status":"STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED"},
      "canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json":{"runner":{"source_exact_match":True,"tests_run":6,"tests_passed":6},"heldout_selection":{"result":"BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED__X"}},
      "canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json":{"status":"INDEPENDENT_VERIFICATION_PASS__X","runner":{"exact_source_match":True,"conclusion":"success"},"donor_runtime_required":False,"independently_verified_behaviors":["SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS"]},
      "canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json":{"status":"FROZEN_X","benchmark_ref":REF,"target_success_fraction":0.664,"replay":False,"cherry_picking":False},
      "canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json":{"status":"ACTIVE_GENERIC_PROTOCOL__X","fail_closed":True,"pass_rule":"BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"},
      "canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json":{"staged_admission":{"stage_a_pre_exposure":{"required":["TARGET_VERSION_LOCK","QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY","GENERAL_EXECUTION_SURFACE_CERTIFICATE","INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED","REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED","STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED","GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE","NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS"]}}},
      "canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json":{"status":"VERIFIED_AND_MERGED__RANK15_REVOCATION_ESCAPE_CLASS_BLOCKED","runner":{"verification_tests_failed":0,"verification_tests_passed":9}}
    }

def materialize(root, ledger):
    files=deps(); files[LEDGER]=ledger
    for p,o in files.items():
        q=Path(root)/p; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(o))

class TestRank17StageA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger=json.loads((Path(__file__).parent/"data_anonymization_rank17_ledger.json").read_text())
    def run_case(self, ledger):
        with tempfile.TemporaryDirectory() as td:
            materialize(td,ledger)
            return evaluate(Path(td),LEDGER,TASK,RANK,HASH)
    def test_exact_rank17_ledger_passes_stage_a_only(self):
        out=self.run_case(self.ledger)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["authorization"],"STAGE_B_INSTRUCTION_EXPOSURE_ONLY")
        self.assertFalse(out["task_execution_authorized"])
    def test_all_eight_exposure_surfaces_present_and_zero(self):
        e=self.ledger["prior_exposure_search"]
        fields=["brain_code_hits","runner_code_hits","brain_branch_hits","runner_branch_hits","brain_commit_hits","runner_commit_hits","brain_pr_hits","runner_pr_hits"]
        self.assertTrue(e["search_complete"])
        self.assertTrue(all(k in e for k in fields))
        self.assertTrue(all(e[k]==0 for k in fields))
    def test_brain_pr_hit_kills_admission(self):
        x=json.loads(json.dumps(self.ledger)); x["prior_exposure_search"]["brain_pr_hits"]=1
        out=self.run_case(x); self.assertFalse(out["pass"]); self.assertIn("PRIOR_EXPOSURE_SEARCH_NOT_CLEAN",out["failed_predicates"])
    def test_missing_brain_pr_surface_kills_admission(self):
        x=json.loads(json.dumps(self.ledger)); del x["prior_exposure_search"]["brain_pr_hits"]
        out=self.run_case(x); self.assertFalse(out["pass"]); self.assertIn("PRIOR_EXPOSURE_SEARCH_FIELDS_MISSING",out["failed_predicates"])
    def test_incomplete_search_flag_kills_admission(self):
        x=json.loads(json.dumps(self.ledger)); x["prior_exposure_search"]["search_complete"]=False
        out=self.run_case(x); self.assertFalse(out["pass"]); self.assertIn("PRIOR_EXPOSURE_SEARCH_INCOMPLETE",out["failed_predicates"])
    def test_instruction_read_kills_admission(self):
        x=json.loads(json.dumps(self.ledger)); x["instruction_read"]=True
        self.assertFalse(self.run_case(x)["pass"])
if __name__=="__main__": unittest.main(verbosity=2)
