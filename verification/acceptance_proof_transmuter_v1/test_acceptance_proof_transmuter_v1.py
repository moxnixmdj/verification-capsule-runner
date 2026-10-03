import json
import unittest
from pathlib import Path
from acceptance_proof_transmuter_v1 import evaluate

ROOT = Path(__file__).resolve().parent

def protocols():
    return {"protocols":[
        {"family":"OWNED","proof_mode":"THEORETICAL_CEILING","status":"PASS"},
        {"family":"MATCHED","proof_mode":"MATCHED_DIRECT_NONINFERIORITY","status":"DEFINED_RESULT_OPEN"},
        {"family":"PUBLIC","proof_mode":"PUBLIC_FIXED_BAR","status":"DEFINED_RESULT_OPEN"},
        {"family":"MIXED","proof_mode":"PUBLIC_FIXED_BAR_PLUS_SCOPE_AUDIT","status":"DEFINED_RESULT_OPEN"},
    ]}

def ev(**kw):
    x={"id":"E1","family":"MATCHED","mode":"UNIVERSAL","verified":True,"independent":True,
       "contamination_clean":True,"binds_frozen_protocol":True,"scope_relation":"EXACT",
       "closes_entire_protocol":True,
       "result":{"all_admissible_inputs_proved":True,"formal_completeness":True}}
    x.update(kw); return x

class Tests(unittest.TestCase):
    def row(self,out,name): return next(r for r in out["families"] if r["family"]==name)

    def test_already_pass_preserved(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[]}),"OWNED")["result_status"],"PASS")

    def test_full_scope_universal_closes(self):
        r=self.row(evaluate(protocols(),{"evidence":[ev()]}),"MATCHED")
        self.assertEqual((r["result_status"],r["closure_mode"]),("PASS","UNIVERSAL"))

    def test_behavioral_only_never_closes(self):
        e=ev(mode="BEHAVIORAL_ONLY",result={"all_admissible_inputs_proved":True,"formal_completeness":True})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_partial_scope_never_closes(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[ev(scope_relation="PARTIAL")]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_unverified_never_closes(self):
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[ev(verified=False)]}),"MATCHED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_theoretical_ceiling_dominance(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",result={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0})
        r=self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")
        self.assertEqual((r["result_status"],r["witness_reason"]),("PASS","THEORETICAL_CEILING_DOMINANCE"))

    def test_target_bound_squeeze(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",result={"direction":"higher","brain_lower_bound":0.94,"target_upper_bound":0.91})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"PASS")

    def test_lower_is_better_floor(self):
        e=ev(mode="ABSOLUTE_DOMINANCE",result={"direction":"lower","brain_upper_bound":0.0,"theoretical_lower_bound":0.0})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MATCHED")["result_status"],"PASS")

    def test_partial_public_bar_cannot_close_composite(self):
        e=ev(id="M",family="MIXED",mode="PUBLIC_FIXED_BAR",closes_entire_protocol=False,result={"threshold_pass":True})
        self.assertEqual(self.row(evaluate(protocols(),{"evidence":[e]}),"MIXED")["result_status"],"DEFINED_RESULT_OPEN")

    def test_malformed_evidence_fails_closed(self):
        self.assertEqual(evaluate(protocols(),{"evidence":"bad"})["status"],"FAIL_CLOSED")

    def test_frozen_live_input_remains_2_closed_17_open(self):
        p=json.loads((ROOT/"OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json").read_text())
        e=json.loads((ROOT/"OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json").read_text())
        out=evaluate(p,e)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual((out["family_count"],out["closed_family_count"],out["open_family_count"]),(19,2,17))
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)


class RecoveryCurrentIntegrationTests(unittest.TestCase):
    def test_current_recovery_universal_witness_closes_exactly_one_new_family(self):
        from recovery_current_acceptance_proof_transmuter_v1 import evaluate as current_evaluate
        p=json.loads((ROOT/"RECOVERY_CURRENT_OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json").read_text())
        e=json.loads((ROOT/"RECOVERY_CURRENT_OPUS55_ACCEPTANCE_INPUT_V2.json").read_text())
        out=current_evaluate(p,e)
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual((out["family_count"],out["closed_family_count"],out["open_family_count"]),(19,4,15),out)
        closed={r["family"] for r in out["families"] if r["result_status"]=="PASS"}
        self.assertEqual(closed,{
            "LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "SUBAGENT_DELEGATION_AND_COORDINATION",
            "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            "EXACT_SYMBOLIC_COMPUTATION",
        },out)
        rr=next(r for r in out["families"] if r["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertEqual(rr["closure_mode"],"UNIVERSAL",rr)
        self.assertEqual(rr["witness_id"],"RECOVERY_P1_UNIVERSAL_STRONGER_PROOF_V2",rr)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
