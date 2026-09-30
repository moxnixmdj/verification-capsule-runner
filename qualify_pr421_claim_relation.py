#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, re, unittest
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parents[0]
PRODUCER=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_claim_relation.py"
EXPECTED_BLOB="f4ee15d04e59e9f677678d3934d74a07f946b99d"

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load_producer():
    s=importlib.util.spec_from_file_location("pr421_claim_relation",PRODUCER)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

NUM_RE=re.compile(r"^\s*([-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
def parse(raw):
    m=NUM_RE.fullmatch(str(raw))
    if not m: raise ValueError("BAD")
    return Decimal(m.group(1)), " ".join(m.group(2).split()).lower()

def independent_relation(a,b,op,threshold=None):
    av,au=parse(a); bv,bu=parse(b)
    if au!=bu: raise ValueError("UNIT_MISMATCH")
    if op=="LT": return av<bv
    if op=="LTE": return av<=bv
    if op=="GT": return av>bv
    if op=="GTE": return av>=bv
    if op=="EQ": return av==bv
    if op=="NE": return av!=bv
    if op=="ABS_DIFF_LTE":
        tv,tu=parse(threshold)
        if tu!=au or tv<0: raise ValueError("THRESHOLD")
        return abs(av-bv)<=tv
    raise ValueError("OP")

def extraction(rows,url):
    return {
      "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
      "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
      "output_verified":True,
      "fresh_url":url,
      "evidence_records":[
        {
          "record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE",
          "ordinal":i,
          "text":text,
          "text_sha256":hashlib.sha256(text.encode()).hexdigest(),
          "numeric_literals":nums,
          "source_url":url,
        } for i,(text,nums) in enumerate(rows)
      ],
    }

class IndependentQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=load_producer()

    def test_exact_candidate_blob(self):
        self.assertEqual(git_blob(PRODUCER),EXPECTED_BLOB)

    def test_fresh_cross_domain_relations(self):
        cases=[
          ("CLIMATE",
           extraction([
             ("Atmospheric carbon dioxide reached 425.6 ppm in the observation period.",["425.6 ppm"]),
             ("The comparison reference was 420.1 ppm.",["420.1 ppm"])
           ],"https://climate.example/evidence"),
           {"mode":"NUMERIC_RELATION","operator":"GT","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0}},
           True),
          ("ASTRONOMY",
           extraction([
             ("The reported orbital period is 365.256 days.",["365.256 days"]),
             ("The comparison period is 400 days.",["400 days"])
           ],"https://astronomy.example/evidence"),
           {"mode":"NUMERIC_RELATION","operator":"LT","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0}},
           True),
          ("MATERIALS",
           extraction([
             ("The measured stress was 251 MPa.",["251 MPa"]),
             ("The reference stress was 250 MPa and the allowed delta was 2 MPa.",["250 MPa","2 MPa"])
           ],"https://materials.example/evidence"),
           {"mode":"NUMERIC_RELATION","operator":"ABS_DIFF_LTE","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0},"threshold":{"record_ordinal":1,"numeric_literal_index":1}},
           True),
        ]
        for domain,data,spec,expected in cases:
            out=self.p.evaluate(data,spec)
            left=data["evidence_records"][spec["left"]["record_ordinal"]]["numeric_literals"][spec["left"]["numeric_literal_index"]]
            right=data["evidence_records"][spec["right"]["record_ordinal"]]["numeric_literals"][spec["right"]["numeric_literal_index"]]
            threshold=None
            if spec["operator"]=="ABS_DIFF_LTE":
                rr=spec["threshold"]
                threshold=data["evidence_records"][rr["record_ordinal"]]["numeric_literals"][rr["numeric_literal_index"]]
            oracle=independent_relation(left,right,spec["operator"],threshold)
            self.assertEqual(out["predicate"],expected,domain)
            self.assertEqual(out["predicate"],oracle,domain)
            self.assertEqual(out["status"],"RELATION_VERIFIED",domain)
            self.assertEqual(out["model_dependency_count"],0,domain)

    def test_verbatim_support_and_paraphrase_rejection(self):
        data=extraction([
          ("The reference implementation guarantees crash consistency after the journal commit.",[])
        ],"https://systems.example/evidence")
        yes=self.p.evaluate(data,{"mode":"VERBATIM_TEXT","claim_text":"guarantees crash consistency after the journal commit"})
        no=self.p.evaluate(data,{"mode":"VERBATIM_TEXT","claim_text":"ensures durable recovery after a transaction"})
        self.assertEqual(yes["status"],"SUPPORT_VERIFIED")
        self.assertEqual(no["status"],"SUPPORT_NOT_VERIFIED")
        passage=" ".join(data["evidence_records"][0]["text"].split()).casefold()
        self.assertIn("guarantees crash consistency after the journal commit".casefold(),passage)
        self.assertNotIn("ensures durable recovery after a transaction".casefold(),passage)

    def test_unit_mismatch_fails_closed(self):
        data=extraction([
          ("One result was 10 m.",["10 m"]),
          ("Another result was 11 s.",["11 s"])
        ],"https://physics.example/evidence")
        with self.assertRaisesRegex(ValueError,"UNIT_MISMATCH"):
            self.p.evaluate(data,{"mode":"NUMERIC_RELATION","operator":"LT","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0}})

if __name__=="__main__":
    unittest.main(verbosity=2)
