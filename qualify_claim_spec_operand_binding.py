#!/usr/bin/env python3
# synchronize-current-pr447-capsule
from __future__ import annotations
import hashlib, importlib.util, pathlib, re, unittest
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
PRODUCER=ROOT/"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"
EXPECTED_PRODUCER_BLOB="34c6851f859a9f1575f0b64c8aac85611e817f29"

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

def extraction(rows):
    texts=[text for text in rows]
    page=sha(b"fresh-independent-page")
    visible="\n".join(texts)
    vis=sha(visible)
    units=[]
    offset=0
    for text in texts:
        t=sha(text); start=offset; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{t}")
        units.append({
            "evidence_unit_id":uid,
            "source_url":"https://independent.example/evidence",
            "page_raw_sha256":page,
            "visible_text_sha256":vis,
            "text":text,
            "text_sha256":t,
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

def number_unit(text):
    rx=re.compile(r"(?<![A-Za-z0-9_.])([-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?")
    rows=[]
    for m in rx.finditer(text):
        rows.append((Decimal(m.group(1)), " ".join(str(m.group(2) or "").split()).lower().rstrip(".,;:")))
    return rows

class IndependentQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate=load_candidate()

    def test_exact_producer_blob(self):
        self.assertEqual(git_blob(PRODUCER),EXPECTED_PRODUCER_BLOB)

    def _case(self,domain,objective,left_text,right_text,expected_operator,expected_predicate,left_anchor,right_anchor):
        data=extraction([left_text,right_text])
        out=self.candidate.bind(objective,data,evaluate_relation=True)
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",(domain,out))
        self.assertEqual(out["relation_spec"]["operator"],expected_operator,(domain,out))
        self.assertEqual(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",(domain,out))

        # Independent role oracle: each anchor must occur in exactly one distinct evidence unit.
        left_hits=[i for i,u in enumerate(data["evidence_units"]) if left_anchor.lower() in u["text"].lower()]
        right_hits=[i for i,u in enumerate(data["evidence_units"]) if right_anchor.lower() in u["text"].lower()]
        self.assertEqual(left_hits,[0],domain)
        self.assertEqual(right_hits,[1],domain)
        self.assertNotEqual(left_hits[0],right_hits[0],domain)

        lv=number_unit(left_text); rv=number_unit(right_text)
        self.assertEqual(len(lv),1,(domain,lv))
        self.assertEqual(len(rv),1,(domain,rv))
        self.assertEqual(lv[0][1],rv[0][1],domain)
        if expected_operator=="GT":
            oracle=lv[0][0] > rv[0][0]
        elif expected_operator=="LT":
            oracle=lv[0][0] < rv[0][0]
        else:
            self.fail("unexpected operator")
        self.assertEqual(oracle,expected_predicate,domain)
        self.assertEqual(out["relation_result"]["predicate"],oracle,(domain,out))

        left_uid=data["evidence_units"][0]["evidence_unit_id"]
        right_uid=data["evidence_units"][1]["evidence_unit_id"]
        self.assertEqual(out["relation_spec"]["left"]["evidence_unit_id"],left_uid,domain)
        self.assertEqual(out["relation_spec"]["right"]["evidence_unit_id"],right_uid,domain)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",domain)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED",domain)
        self.assertEqual(out["model_dependency_count"],0,domain)

    def test_fresh_cross_domain_bindings(self):
        cases=[
          (
            "HYDROLOGY",
            "Determine whether River Alpha annual discharge is higher than River Beta annual discharge.",
            "River Alpha annual discharge was 1250 m3/s.",
            "River Beta annual discharge was 980 m3/s.",
            "GT",True,"River Alpha","River Beta"
          ),
          (
            "ASTRONOMY",
            "Determine whether Star Vega surface temperature is lower than Star Sirius surface temperature.",
            "Star Vega surface temperature was 9602 K.",
            "Star Sirius surface temperature was 9940 K.",
            "LT",True,"Star Vega","Star Sirius"
          ),
          (
            "DATABASE_SYSTEMS",
            "Does Database A checkpoint latency exceed Database B checkpoint latency?",
            "Database A checkpoint latency was 42 ms.",
            "Database B checkpoint latency was 35 ms.",
            "GT",True,"Database A","Database B"
          ),
          (
            "MATERIALS",
            "Determine whether basalt density is lower than granite density.",
            "Basalt density was 2.90 g/cm3.",
            "Granite density was 2.70 g/cm3.",
            "LT",False,"Basalt","Granite"
          ),
        ]
        for row in cases:
            self._case(*row)

    def test_ambiguity_fails_closed_independently(self):
        data=extraction([
          "River Alpha annual discharge was 1250 m3/s.",
          "River Alpha annual discharge in the second gauge was 1240 m3/s.",
          "River Beta annual discharge was 980 m3/s.",
        ])
        out=self.candidate.bind(
          "Determine whether River Alpha annual discharge is higher than River Beta annual discharge.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY",out)

    def test_multiple_values_fail_closed_independently(self):
        data=extraction([
          "Star Vega surface temperature was 9602 K and revised to 9610 K.",
          "Star Sirius surface temperature was 9940 K.",
        ])
        out=self.candidate.bind(
          "Determine whether Star Vega surface temperature is lower than Star Sirius surface temperature.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR",out)

    def test_unsupported_language_fails_closed(self):
        data=extraction([
          "River Alpha annual discharge was 1250 m3/s.",
          "River Beta annual discharge was 980 m3/s.",
        ])
        out=self.candidate.bind("Compare River Alpha with River Beta annual discharge.",data,evaluate_relation=False)
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
