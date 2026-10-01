import unittest
from rank15_stage_a_admission import evaluate

def good():
    return {
      "target_lock":{"status":"FROZEN_STAGE_A_LOCAL_QUALIFICATION_SCOPE","target_model":"Claude Opus 5.5","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","acceptance_bar":{"success_fraction":0.664},"sample_manifest":{"rank15_task":"wdm-design","rank15_identity_sha256":"57a897eff90387df26415d1bfb81c492d50b4d41159587617bfefda8c2f2bf8d"}},
      "contamination":{"task":"wdm-design","rank":15,"task_identity_sha256":"57a897eff90387df26415d1bfb81c492d50b4d41159587617bfefda8c2f2bf8d","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","state":"UNEXPOSED__STAGE_A_PRE_EXPOSURE","instruction_read":False,"hidden_verifier_read":False,"task_specific_hints_read":False,"task_specific_web_or_repo_search":False,"task_command_executed":False,"clean_for_stage_b_exposure":True},
      "surface":{"status":"STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED","verified":[{"conclusion":"success"}]},
      "acceptance":{"runner":{"source_exact_match":True,"tests_run":6,"tests_passed":6},"integration_rule":"MAY_BE_USED_AS_A_NECESSARY_FAIL_CLOSED_TERMINAL_GATE_ONLY__MUST_NOT_BE_TREATED_AS_SUFFICIENT_TERMINAL_AUTHORITY"},
      "requirement_graph":{"status":"INDEPENDENT_VERIFICATION_PASS__BRAIN_OWNED_NARROW_COMPONENT__ZERO_FAMILY_CREDIT","runner":{"exact_source_match":True,"conclusion":"success"},"independently_verified_behaviors":["SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS"]},
      "statistics":{"status":"FROZEN_BEFORE_RANK15_INSTRUCTION_EXPOSURE","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","target_success_fraction":0.664,"replay":False,"cherry_picking":False,"sequential_promotion":{"no_promotion_from_point_estimate_alone":True}},
      "donor_protocol":{"status":"STAGE_A_PROTOCOL_AVAILABLE__NOT_DONOR_DELETION_EVIDENCE__ZERO_CREDIT","actual_donor_deletion_passed":False,"mandatory_for_donor_derived_promotion":[
        "ENUMERATE_ALL_UNAVOIDABLE_RUNTIME_DEPENDENCIES_INCLUDING_BASE_MODELS_SERVICES_LIBRARIES_AND_LEARNED_SUBSTRATES",
        "PHYSICALLY_REMOVE_OR_DENY_THE_DONOR_AS_TARGET_CAPABILITY_PROVIDER_WHERE_APPLICABLE",
        "RUN_THE_EXACT_BRAIN_ROUTE_IN_A_CLEAN_ROOM_WITH_DONOR_TARGET_CAPABILITY_ACCESS_UNAVAILABLE",
        "FAIL_PROMOTION_IF_TARGET_BEHAVIOR_DISAPPEARS_OR_AN_UNDISCLOSED_DEPENDENCY_IS_REQUIRED"
      ]}
    }

class StageA(unittest.TestCase):
  def test_pass_is_exposure_only(self):
    out=evaluate(good())
    self.assertTrue(out["pass"])
    self.assertTrue(out["authorize_instruction_exposure"])
    self.assertFalse(out["authorize_task_execution"])
    self.assertFalse(out["terminal_goal_achieved"])

  def test_exposure_fails_closed(self):
    x=good(); x["contamination"]["instruction_read"]=True
    self.assertFalse(evaluate(x)["pass"])

  def test_wrong_target_fails(self):
    x=good(); x["target_lock"]["benchmark_ref"]="wrong"
    self.assertFalse(evaluate(x)["pass"])

  def test_acceptance_and_requirement_proof_required(self):
    x=good(); x["acceptance"]["runner"]["tests_passed"]=5
    self.assertFalse(evaluate(x)["pass"])
    y=good(); y["requirement_graph"]["runner"]["conclusion"]="failure"
    self.assertFalse(evaluate(y)["pass"])

  def test_protocol_not_evidence(self):
    x=good(); x["donor_protocol"]["actual_donor_deletion_passed"]=True
    out=evaluate(x)
    self.assertFalse(out["pass"])
    self.assertIn("DONOR_PROTOCOL_CONFUSES_PLAN_WITH_EVIDENCE",out["failed_predicates"])

if __name__=="__main__":
  unittest.main(verbosity=2)
