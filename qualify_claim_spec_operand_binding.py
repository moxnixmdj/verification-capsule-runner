#!/usr/bin/env python3
# synchronize-latest-pr447-capsule-v2
from __future__ import annotations
import hashlib, importlib.util, pathlib, re, unittest
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
PRODUCER=ROOT/"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"
EXPECTED_PRODUCER_BLOB="48fd058430d8d361fc75beced567c7b6d1166531"

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load_candidate():
    spec=importlib.util.spec_from_file_location("candidate_claim_binding",PRODUCER)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def sha(v):
    if isinstance(v,str): v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()

def extraction(texts):
    page=sha(b"independent-fresh-page")
    visible="\n".join(texts)
    vis=sha(visible)
    units=[]; offset=0
    for text in texts:
        tsha=sha(text); start=offset; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        units.append({
          "evidence_unit_id":uid,
          "source_url":"https://independent.example/evidence",
          "page_raw_sha256":page,
          "visible_text_sha256":vis,
          "text":text,
          "text_sha256":tsha,
          "visible_text_start":start,
          "visible_text_end":end,
        })
        offset=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://independent.example/evidence",
      "page_raw_sha256":page,
      "visible_text_sha256":vis,
      "evidence_units":units,
    }

NUM=re.compile(r"(?<![A-Za-z0-9_.])([-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?")
def one_value(text):
    rows=[(Decimal(m.group(1)),str(m.group(2) or "").lower().rstrip(".,;:")) for m in NUM.finditer(text)]
    return rows

class IndependentQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=load_candidate()

    def test_exact_producer_blob(self):
        self.assertEqual(git_blob(PRODUCER),EXPECTED_PRODUCER_BLOB)

    def _numeric_case(self,domain,objective,left,right,operator,expected):
        data=extraction([left,right])
        out=self.c.bind(objective,data,evaluate_relation=True)
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",(domain,out))
        self.assertEqual(out["relation_spec"]["operator"],operator,(domain,out))
        self.assertEqual(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",(domain,out))
        lv=one_value(left); rv=one_value(right)
        # Cases below deliberately contain exactly one semantic quantity each.
        self.assertEqual(len(lv),1,(domain,lv))
        self.assertEqual(len(rv),1,(domain,rv))
        self.assertEqual(lv[0][1],rv[0][1],domain)
        a,b=lv[0][0],rv[0][0]
        oracle={
          "GT":a>b,"LT":a<b,"GTE":a>=b,"LTE":a<=b,"EQ":a==b,"NE":a!=b
        }[operator]
        self.assertEqual(oracle,expected,domain)
        self.assertEqual(out["relation_result"]["predicate"],oracle,(domain,out))
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",domain)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED",domain)
        self.assertEqual(out["model_dependency_count"],0,domain)

    def test_fresh_cross_domain_operator_surface(self):
        cases=[
          ("HYDROLOGY","Determine whether River Alpha annual discharge is higher than River Beta annual discharge.",
           "River Alpha annual discharge was 1250 m3/s.","River Beta annual discharge was 980 m3/s.","GT",True),
          ("ASTRONOMY","Determine whether Star Vega surface temperature is lower than Star Sirius surface temperature.",
           "Star Vega surface temperature was 9602 K.","Star Sirius surface temperature was 9940 K.","LT",True),
          ("DATABASES","Determine whether Database A checkpoint latency is at most Database B checkpoint latency.",
           "Database A checkpoint latency was 42 ms.","Database B checkpoint latency was 35 ms.","LTE",False),
          ("MATERIALS","Determine whether Alloy X yield strength is at least Alloy Y yield strength.",
           "Alloy X yield strength was 310 MPa.","Alloy Y yield strength was 300 MPa.","GTE",True),
          ("CHEMISTRY","Determine whether Sample A pH is equal to Sample B pH.",
           "Sample A pH was 7.2 pH.","Sample B pH was 7.2 pH.","EQ",True),
          ("ENERGY","Determine whether Reactor A output is different from Reactor B output.",
           "Reactor A output was 510 MW.","Reactor B output was 500 MW.","NE",True),
        ]
        for row in cases: self._numeric_case(*row)

    def test_abs_diff_threshold_independent_oracle(self):
        data=extraction([
          "Sensor Alpha temperature was 20.2 C.",
          "Sensor Beta temperature was 20.5 C.",
        ])
        out=self.c.bind(
          "Determine whether Sensor Alpha temperature and Sensor Beta temperature differ by at most 0.5 C.",
          data,evaluate_relation=True
        )
        self.assertEqual(out["relation_spec"]["operator"],"ABS_DIFF_LTE",out)
        self.assertEqual(out["relation_spec"]["threshold"],"0.5 C",out)
        oracle=abs(Decimal("20.2")-Decimal("20.5"))<=Decimal("0.5")
        self.assertTrue(oracle)
        self.assertEqual(out["relation_result"]["predicate"],oracle,out)

    def test_exact_quoted_claim_binding_independent(self):
        claim="The protocol retries after 5 seconds."
        data=extraction([
          "Operational notes state: The protocol retries after 5 seconds. This is the default.",
          "Separate material discusses timeouts."
        ])
        out=self.c.bind(f'Verify whether the evidence states "{claim}"',data,evaluate_relation=True)
        self.assertEqual(out["status"],"CLAIM_SPEC_BOUND",out)
        self.assertEqual(out["relation_spec"]["mode"],"VERBATIM_SUPPORT",out)
        self.assertEqual(out["relation_result"]["status"],"EXACT_TEXT_SUPPORT_VERIFIED",out)
        hits=[u for u in data["evidence_units"] if claim.casefold() in u["text"].casefold()]
        self.assertEqual(len(hits),1)
        self.assertEqual(out["claim_binding"]["evidence_unit_id"],hits[0]["evidence_unit_id"])

    def test_single_letter_labels_are_semantically_distinct(self):
        data=extraction([
          "Planet Kepler A orbital period was 120 days.",
          "Planet Kepler B orbital period was 180 days.",
        ])
        out=self.c.bind(
          "Planet Kepler A orbital period exceeds Planet Kepler B orbital period.",
          data,evaluate_relation=True
        )
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertFalse(out["relation_result"]["predicate"],out)
        self.assertIn("label:a",out["parsed_objective"]["left_tokens"])
        self.assertIn("label:b",out["parsed_objective"]["right_tokens"])

    def test_full_coverage_role_ambiguity_fails_closed(self):
        data=extraction([
          "River Alpha annual discharge was 1250 m3/s.",
          "River Alpha annual discharge at second gauge was 1240 m3/s.",
          "River Beta annual discharge was 980 m3/s.",
        ])
        out=self.c.bind(
          "Determine whether River Alpha annual discharge is higher than River Beta annual discharge.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY",out)

    def test_multiple_compatible_values_fail_closed(self):
        data=extraction([
          "Star Vega surface temperature was 9602 K and revised to 9610 K.",
          "Star Sirius surface temperature was 9940 K.",
        ])
        out=self.c.bind(
          "Determine whether Star Vega surface temperature is lower than Star Sirius surface temperature.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR",out)

    def test_threshold_unit_mismatch_fails_closed(self):
        data=extraction([
          "Sensor Alpha temperature was 20.2 C.",
          "Sensor Beta temperature was 20.5 C.",
        ])
        with self.assertRaisesRegex(ValueError,"THRESHOLD_UNIT_MISMATCH"):
            self.c.bind(
              "Determine whether Sensor Alpha temperature and Sensor Beta temperature differ by at most 0.5 K.",
              data,evaluate_relation=True
            )

    def test_unsupported_language_fails_closed(self):
        data=extraction([
          "River Alpha annual discharge was 1250 m3/s.",
          "River Beta annual discharge was 980 m3/s.",
        ])
        out=self.c.bind("Compare River Alpha and River Beta annual discharge.",data,evaluate_relation=False)
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
