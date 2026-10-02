import unittest
from acceptance_proof_transmuter_v1 import evaluate

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

if __name__=="__main__":
    unittest.main(verbosity=2)
