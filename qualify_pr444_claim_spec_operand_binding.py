#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import importlib.util
import pathlib
import re
import urllib.request
import unittest
from html.parser import HTMLParser
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
PRODUCER=ROOT/"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"

SQLITE_URL="https://www.sqlite.org/limits.html"
NIST_URL="https://www.nist.gov/pml/owm/si-units-temperature"
UA="ProjectBrain-Independent-OperandBinding-Qualification/1.0"

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","svg"}: self.skip+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","svg"} and self.skip: self.skip-=1
    def handle_data(self,data):
        if self.skip:return
        t=" ".join(str(data or "").split())
        if t:self.parts.append(t)

def canon(x):
    return " ".join(str(x or "").split())

def fetch_visible(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,*/*;q=0.4"})
    with urllib.request.urlopen(req,timeout=25) as r:
        raw=r.read(2_000_000)
        final=r.geturl()
        status=int(getattr(r,"status",200))
    p=Visible(); p.feed(raw.decode("utf-8","replace"))
    visible=html.unescape(" ".join(p.parts))
    return raw,canon(visible),final,status

def sha(x):
    if isinstance(x,str):x=x.encode()
    return hashlib.sha256(x).hexdigest()

def load_candidate():
    s=importlib.util.spec_from_file_location("pr444_operand_binder",PRODUCER)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def extraction_from_live(raw,url,snippets):
    visible="\n".join(snippets)
    page=sha(raw); vsha=sha(visible)
    rows=[]; offset=0
    for text in snippets:
        text=canon(text); start=offset; end=start+len(text); tsha=sha(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({
          "evidence_unit_id":uid,
          "source_url":url,
          "page_raw_sha256":page,
          "visible_text_sha256":vsha,
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
      "source_url":url,
      "page_raw_sha256":page,
      "visible_text_sha256":vsha,
      "evidence_units":rows,
    }

def require_regex(visible,pattern,label):
    m=re.search(pattern,visible,re.I)
    if not m:
        raise AssertionError(label+"_LIVE_SOURCE_PATTERN_MISSING")
    return canon(m.group(0)),m

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=load_candidate()

    def test_live_sqlite_role_binding_and_lt_relation(self):
        raw,visible,final,status=fetch_visible(SQLITE_URL)
        self.assertEqual(status,200)
        left,lm=require_regex(
            visible,
            r"(?:The\s+)?default setting for SQLITE_MAX_COLUMN is\s+([0-9,]+)\.",
            "SQLITE_LEFT",
        )
        right,rm=require_regex(
            visible,
            r"(?:So\s+)?there is a hard upper bound on SQLITE_MAX_FUNCTION_ARG of\s+([0-9,]+)\.",
            "SQLITE_RIGHT",
        )
        lv=Decimal(lm.group(1).replace(",","")); rv=Decimal(rm.group(1).replace(",",""))
        self.assertLess(lv,rv)
        data=extraction_from_live(raw,final,[left,right])
        objective="Determine whether default setting SQLITE_MAX_COLUMN is lower than hard upper bound SQLITE_MAX_FUNCTION_ARG."
        out=self.p.bind(objective,data)
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"LT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertIn("SQLITE_MAX_COLUMN",out["left_binding"]["text"])
        self.assertIn("SQLITE_MAX_FUNCTION_ARG",out["right_binding"]["text"])
        self.assertEqual(Decimal(out["relation_result"]["left"]["value"]),lv)
        self.assertEqual(Decimal(out["relation_result"]["right"]["value"]),rv)

    def test_live_nist_hot_nice_role_binding_and_gt_relation(self):
        raw,visible,final,status=fetch_visible(NIST_URL)
        self.assertEqual(status,200)
        left,lm=require_regex(visible,r"30\s*°C\s+is\s+hot","NIST_LEFT")
        right,rm=require_regex(visible,r"20\s*°C\s+is\s+nice","NIST_RIGHT")
        data=extraction_from_live(raw,final,[left,right])
        objective="Determine whether hot is higher than nice."
        out=self.p.bind(objective,data)
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertIn("hot",out["left_binding"]["text"].lower())
        self.assertIn("nice",out["right_binding"]["text"].lower())
        self.assertEqual(Decimal(out["relation_result"]["left"]["value"]),Decimal("30"))
        self.assertEqual(Decimal(out["relation_result"]["right"]["value"]),Decimal("20"))
        self.assertEqual(out["relation_result"]["left"]["unit"].lower(),"°c")
        self.assertEqual(out["relation_result"]["right"]["unit"].lower(),"°c")

    def test_independent_negative_ambiguity_and_no_overclaim(self):
        raw,visible,final,status=fetch_visible(NIST_URL)
        left,_=require_regex(visible,r"30\s*°C\s+is\s+hot","NIST_LEFT")
        right,_=require_regex(visible,r"20\s*°C\s+is\s+nice","NIST_RIGHT")
        data=extraction_from_live(raw,final,[left,left,right])
        out=self.p.bind("Determine whether hot is higher than nice.",data,evaluate_relation=False)
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY",out)

        clean=extraction_from_live(raw,final,[left,right])
        ok=self.p.bind("Determine whether hot is higher than nice.",clean)
        self.assertEqual(ok["factual_correctness_status"],"UNVERIFIED")
        self.assertEqual(ok["semantic_entailment_status"],"UNVERIFIED")
        self.assertEqual(ok["evidence_sufficiency_status"],"UNVERIFIED")
        self.assertEqual(ok["model_dependency_count"],0)
        self.assertEqual(ok["incremental_spend_usd"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
