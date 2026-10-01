import json, tempfile, unittest
from pathlib import Path
from prequalification_stage_a_generic import evaluate

LEDGER="canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json"
TASK="data-anonymization"
RANK=17
HASH="65c02927e5914f433922f83db07e89608b906e383c6bed904f452640238bd31c"

REQUIRED_POLICY=[
    "TARGET_VERSION_LOCK",
    "QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY",
    "COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS",
    "GENERAL_EXECUTION_SURFACE_CERTIFICATE",
    "INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED",
    "REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED",
    "STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED",
    "GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE",
    "NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS",
]

FILES={
"canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json":{"status":"FROZEN_X","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","stage1_target_success_fraction":0.664,"target_model":"Claude Opus 5.5"},
LEDGER:{"task":TASK,"rank":RANK,"task_identity_sha256":HASH,"benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","state":"UNEXPOSED__STAGE_A_PRE_EXPOSURE","instruction_read":False,"hidden_verifier_read":False,"task_specific_hints_read":False,"task_specific_web_or_repo_search":False,"task_command_executed":False,"clean_for_stage_b_exposure":True,"disqualifying_exposure_events":[],"prior_exposure_search":{"search_complete":True,"brain_code_hits":0,"runner_code_hits":0,"brain_branch_hits":0,"runner_branch_hits":0,"brain_commit_hits":0,"runner_commit_hits":0,"brain_pr_hits":0,"runner_pr_hits":0}},
"canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json":{"status":"STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED"},
"canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json":{"runner":{"source_exact_match":True,"tests_run":6,"tests_passed":6},"heldout_selection":{"result":"BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED__X"}},
"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json":{"status":"INDEPENDENT_VERIFICATION_PASS__X","runner":{"exact_source_match":True,"conclusion":"success"},"donor_runtime_required":False,"independently_verified_behaviors":["SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS"]},
"canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json":{"status":"FROZEN_X","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","target_success_fraction":0.664,"replay":False,"cherry_picking":False},
"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json":{"status":"ACTIVE_GENERIC_PROTOCOL__X","fail_closed":True,"pass_rule":"BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"},
"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json":{"staged_admission":{"stage_a_pre_exposure":{"required":REQUIRED_POLICY}}},
"canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json":{"status":"VERIFIED_AND_MERGED__RANK15_REVOCATION_ESCAPE_CLASS_BLOCKED","runner":{"verification_tests_failed":0,"verification_tests_passed":9}}
}

def materialize(tmp):
    for p,o in FILES.items():
        q=Path(tmp)/p
        q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(json.dumps(o))

class Tests(unittest.TestCase):
    def run_eval(self, mutate=None):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        materialize(td.name)
        if mutate:
            mutate(Path(td.name))
        return evaluate(Path(td.name),LEDGER,TASK,RANK,HASH)

    def test_clean_complete_search_passes(self):
        out=self.run_eval()
        self.assertTrue(out["pass"])
        self.assertFalse(out["task_execution_authorized"])

    def test_each_contamination_bit_fails(self):
        for key in ["instruction_read","hidden_verifier_read","task_specific_hints_read","task_specific_web_or_repo_search","task_command_executed"]:
            with self.subTest(key=key):
                def mutate(root,key=key):
                    p=root/LEDGER; o=json.loads(p.read_text()); o[key]=True; p.write_text(json.dumps(o))
                self.assertFalse(self.run_eval(mutate)["pass"])

    def test_each_prior_exposure_surface_fails_when_nonzero(self):
        keys=["brain_code_hits","runner_code_hits","brain_branch_hits","runner_branch_hits","brain_commit_hits","runner_commit_hits","brain_pr_hits","runner_pr_hits"]
        for key in keys:
            with self.subTest(key=key):
                def mutate(root,key=key):
                    p=root/LEDGER; o=json.loads(p.read_text()); o["prior_exposure_search"][key]=1; p.write_text(json.dumps(o))
                out=self.run_eval(mutate)
                self.assertFalse(out["pass"])
                self.assertIn("PRIOR_EXPOSURE_SEARCH_NOT_CLEAN",out["failed_predicates"])

    def test_missing_brain_pr_surface_fails(self):
        def mutate(root):
            p=root/LEDGER; o=json.loads(p.read_text()); del o["prior_exposure_search"]["brain_pr_hits"]; p.write_text(json.dumps(o))
        out=self.run_eval(mutate)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_SEARCH_FIELDS_MISSING",out["failed_predicates"])

    def test_search_complete_false_fails(self):
        def mutate(root):
            p=root/LEDGER; o=json.loads(p.read_text()); o["prior_exposure_search"]["search_complete"]=False; p.write_text(json.dumps(o))
        out=self.run_eval(mutate)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_SEARCH_INCOMPLETE",out["failed_predicates"])

    def test_policy_omitting_eight_surface_requirement_fails(self):
        def mutate(root):
            p=root/"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"
            o=json.loads(p.read_text())
            o["staged_admission"]["stage_a_pre_exposure"]["required"].remove("COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS")
            p.write_text(json.dumps(o))
        out=self.run_eval(mutate)
        self.assertFalse(out["pass"])
        self.assertIn("STAGE_A_POLICY_INCOMPLETE",out["failed_predicates"])

if __name__=="__main__":
    unittest.main()
