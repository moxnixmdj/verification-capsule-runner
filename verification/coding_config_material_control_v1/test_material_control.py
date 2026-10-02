import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"session_bridge"))
import controller_fast as controller
import acceptance_contract as acceptance

SESSION="synthetic-coding-material-control-v1"

def contract():
    return {
      "schema":"BRAIN_FAST_BURST_ACCEPTANCE_MODEL_V1",
      "session_id":SESSION,
      "frozen_before_builder":True,
      "solution_tests_verifier_exposed":False,
      "behavioral_contract":{
        "behavior_id":"SYNTHETIC_CODING_COMPLETION",
        "inputs":"task instruction and runtime-visible repository",
        "environment_state":"isolated task runtime",
        "allowed_information":"instruction plus runtime-visible files and command outputs",
        "required_output_or_action":"verified task artifact",
        "success_condition":"all explicit acceptance criteria and verification commands pass",
        "failure_condition":"known relevant failure or uncovered acceptance criterion remains",
        "terminal_consequence":"submission allowed only after independent evidence is complete",
        "verification_route":"fresh runtime checks plus independent terminal verifier",
        "dependency_boundary":"declared artifact and runtime dependency closure",
        "scope":"synthetic configuration-control proof only"
      },
      "requirements":[{
        "id":"REQ1","statement":"Do not submit with a known relevant failure.",
        "source_basis":"Brain fail-closed completion contract"
      }],
      "acceptance_checks":[{
        "id":"CHECK1","kind":"INVARIANT",
        "predicted_consequence":"submission is blocked until the requirement is evidenced",
        "evidence_basis":"fresh verification receipt",
        "independence_class":"INDEPENDENT_RUNTIME_CHECK",
        "covers_requirements":["REQ1"]
      }]
    }

def terminal(h):
    return {
      "schema":"BRAIN_FAST_BURST_TERMINAL_AUTHORIZATION_V2",
      "session_id":SESSION,
      "acceptance_contract_sha256":h,
      "submission_authorized":True,
      "known_relevant_failures":[],
      "acceptance_criteria":[{"id":"CHECK1","status":"PASS","evidence":"fresh independent check"}],
      "verification_commands":[{"command":"python -m unittest","exit_code":0}]
    }

class MaterialControl(unittest.TestCase):
    def setUp(self):
        controller.CONFIG={
          "session_id":SESSION,
          "require_canonical_lease_authorization":True,
          "require_acceptance_contract":True,
        }
        self.c=contract()
        self.assertEqual(acceptance.validate_acceptance_payload(self.c,SESSION),[])
        self.h=acceptance.canonical_payload_hash(self.c)
        self.p=terminal(self.h)

    def block(self,p=None,c=None,h=None,lease=True):
        return controller.terminal_blocker(
          self.p if p is None else p,
          self.c if c is None else c,
          self.h if h is None else h,
          lease_authorized=lease,
        )

    def test_complete_brain_configuration_is_terminally_admissible(self):
        self.assertIsNone(self.block())

    def test_deleting_lease_blocks(self):
        self.assertEqual(self.block(lease=False),"CANONICAL_LEASE_NOT_BOUND")

    def test_deleting_acceptance_contract_blocks(self):
        self.assertEqual(controller.terminal_blocker(self.p,None,None,lease_authorized=True),"ACCEPTANCE_CONTRACT_NOT_FROZEN")

    def test_stale_acceptance_hash_blocks(self):
        p=dict(self.p); p["acceptance_contract_sha256"]="0"*64
        self.assertEqual(self.block(p=p),"ACCEPTANCE_CONTRACT_HASH_MISMATCH")

    def test_known_failure_blocks(self):
        p=dict(self.p); p["known_relevant_failures"]=["real failure"]
        self.assertEqual(self.block(p=p),"KNOWN_RELEVANT_FAILURES_REMAIN")

    def test_missing_frozen_check_blocks(self):
        p=dict(self.p); p["acceptance_criteria"]=[]
        self.assertEqual(self.block(p=p),"FROZEN_ACCEPTANCE_CHECK_MISSING:CHECK1")

    def test_failed_frozen_check_blocks(self):
        p=dict(self.p); p["acceptance_criteria"]=[{"id":"CHECK1","status":"FAIL","evidence":"negative"}]
        self.assertEqual(self.block(p=p),"FROZEN_ACCEPTANCE_CHECK_NOT_PASS:CHECK1")

    def test_missing_verification_commands_blocks(self):
        p=dict(self.p); p["verification_commands"]=[]
        self.assertEqual(self.block(p=p),"VERIFICATION_COMMANDS_MISSING")

    def test_failed_verification_command_blocks(self):
        p=dict(self.p); p["verification_commands"]=[{"command":"pytest","exit_code":1}]
        self.assertEqual(self.block(p=p),"VERIFICATION_COMMANDS_NOT_ALL_PASS")

    def test_submission_flag_is_load_bearing(self):
        p=dict(self.p); p["submission_authorized"]=False
        self.assertEqual(self.block(p=p),"SUBMISSION_NOT_AUTHORIZED")

if __name__=="__main__":
    unittest.main(verbosity=2)
