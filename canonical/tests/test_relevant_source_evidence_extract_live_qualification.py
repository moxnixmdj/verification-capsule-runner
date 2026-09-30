#!/usr/bin/env python3
from __future__ import annotations
import html, importlib.util, pathlib, re, urllib.request, unittest
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/relevant_source_evidence_extract.py"

def load():
    s=importlib.util.spec_from_file_location("candidate_extract",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","svg"}: self.skip+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","svg"} and self.skip: self.skip-=1
    def handle_data(self,data):
        if not self.skip:
            t=" ".join(str(data or "").split())
            if t:self.parts.append(t)

def independent_visible(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-Evidence-Oracle/1","Accept":"text/html,text/plain,*/*;q=0.2"})
    with urllib.request.urlopen(req,timeout=20) as r:
        raw=r.read(1500000); ctype=str(r.headers.get("Content-Type") or "")
    text=raw.decode("utf-8","replace")
    if "html" in ctype.lower() or "<html" in text[:1000].lower():
        p=Visible(); p.feed(text); text=html.unescape(" ".join(p.parts))
    return " ".join(text.split())

class LiveQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def _case(self,domain,url,objective):
        out=self.m.extract(
          objective,
          {"url":url},
          {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":url,"final_host":domain},
          {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":domain},
          timeout=20,max_passages=8
        )
        self.assertEqual(out.get("status"),"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED",out)
        self.assertGreater(out.get("evidence_record_count",0),0,out)
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED",out)
        independent=independent_visible(url)
        for rec in out["evidence_records"]:
            self.assertIn(" ".join(rec["text"].split()),independent)
            self.assertTrue(rec["matched_objective_tokens"],rec)
        return out

    def test_live_nist(self):
        self._case("nist.gov","https://www.nist.gov/pqc","Assess NIST post quantum cryptography standards")

    def test_live_who(self):
        self._case("who.int","https://www.who.int/teams/immunization-vaccines-and-biologicals/diseases/malaria","Assess malaria vaccine recommendations for children")

if __name__=="__main__": unittest.main(verbosity=2)
