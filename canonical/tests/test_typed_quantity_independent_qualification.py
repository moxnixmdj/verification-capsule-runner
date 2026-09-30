#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, sys, unittest
from quantulum3 import parser

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_typed_quantity.py"

def load():
    s=importlib.util.spec_from_file_location("producer",P)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def producer(self,text,literals):
        return self.m.extract({
          "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",
          "fresh_url":"https://example.org/source",
          "page_sha256":"a"*64,
          "evidence_records":[{
             "text":text,"text_sha256":"b"*64,"source_url":"https://example.org/source",
             "matched_objective_tokens":["measurement"],"numeric_literals":literals,
          }]
        })

    def compare(self,text,literals):
        out=self.producer(text,literals)
        self.assertEqual(out["status"],"TYPED_QUANTITY_CANDIDATES_EXTRACTED",out)
        independent=parser.parse(text)
        independent_values=[float(x.value) for x in independent]
        producer_values=[float(x["value"]) for x in out["typed_quantity_candidates"]]
        for value in producer_values:
            self.assertTrue(any(abs(value-x)<=max(1e-12,abs(value)*1e-12) for x in independent_values),(value,independent_values,out))
        for q in out["typed_quantity_candidates"]:
            self.assertIn(q["surface"],text)
            self.assertEqual(q["semantic_role_status"],"UNBOUND")
        return out

    def test_temperature_and_viscosity(self):
        self.compare(
          "At 40 °C the viscosity is 0.653 mPa*s and at 20 °C it is 1.002 mPa*s.",
          ["40 °C","0.653 mPa*s","20 °C","1.002 mPa*s"]
        )

    def test_percentage_and_speed(self):
        self.compare(
          "The measured change was 12.5% while the speed was 0.34 km/s.",
          ["12.5%","0.34 km/s"]
        )

    def test_scientific_notation_and_dimensionless(self):
        self.compare(
          "The coefficient was 2.5e-3 and the energy scale was 13.0 TeV.",
          ["2.5e-3","13.0 TeV"]
        )

    def test_no_semantic_overclaim(self):
        x=self.producer("The value was 42 m.",["42 m"])
        self.assertEqual(x["unit_normalization_status"],"NOT_PERFORMED")
        self.assertEqual(x["operand_binding_status"],"NOT_PERFORMED")
        self.assertEqual(x["factual_correctness_status"],"UNVERIFIED")

if __name__=="__main__": unittest.main(verbosity=2)
