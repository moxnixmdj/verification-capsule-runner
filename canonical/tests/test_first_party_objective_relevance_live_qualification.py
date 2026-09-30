#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, subprocess, urllib.parse, urllib.request, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py"
EXPECTED_BLOB="e35cdb2495accc43fd677df495bf120a561b47a3"
ROR="https://api.ror.org/v2/organizations"

def load():
    s=importlib.util.spec_from_file_location("candidate",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def ror_exact(domain,timeout=20):
    url=ROR+"?"+urllib.parse.urlencode({"query.advanced":f'domains:"{domain}"'})
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-ROR-Relevance-Oracle/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read(3000000)
        final=r.geturl()
    if (urllib.parse.urlsplit(final).hostname or "").lower()!="api.ror.org":
        raise AssertionError("ROR_REDIRECT_OUTSIDE_API")
    data=json.loads(raw.decode("utf-8","replace"))
    hits=[]
    for rec in data.get("items") or []:
        if str(rec.get("status") or "").lower()!="active":
            continue
        domains=[]
        for x in rec.get("domains") or []:
            h=str(x or "").lower().strip(".")
            if h.startswith("www."): h=h[4:]
            domains.append(h)
        if domain in domains:
            hits.append(rec)
    return hits

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_exact_candidate_blob(self):
        got=subprocess.check_output(["git","hash-object",str(P)],text=True).strip()
        self.assertEqual(got,EXPECTED_BLOB)

    def _positive(self,domain,url,objective):
        hits=ror_exact(domain)
        self.assertEqual(len(hits),1,(domain,len(hits)))
        rec=hits[0]
        out=self.m.verify(
            objective,
            {"url":url},
            {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":url,"final_host":domain},
            {
              "status":"AUTHORITY_IDENTITY_VERIFIED",
              "matched_domain":domain,
              "organization_name":next(
                  (str(n.get("value")) for n in (rec.get("names") or []) if "ror_display" in (n.get("types") or [])),
                  None,
              ),
            },
            timeout=20,
        )
        self.assertEqual(out.get("status"),"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",out)
        self.assertEqual(out.get("first_party_source_status"),"VERIFIED",out)
        self.assertEqual(out.get("objective_relevance_status"),"VERIFIED",out)
        self.assertEqual(out.get("primary_source_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("model_dependency_count"),0,out)
        self.assertEqual(out.get("incremental_spend_usd"),0,out)

    def test_live_cross_domain_nist(self):
        self._positive(
            "nist.gov",
            "https://www.nist.gov/pqc",
            "Assess NIST post quantum cryptography encryption standards for quantum resistant migration",
        )

    def test_live_cross_domain_who(self):
        self._positive(
            "who.int",
            "https://www.who.int/teams/immunization-vaccines-and-biologicals/diseases/malaria",
            "Assess WHO malaria vaccine recommendations for children in malaria endemic areas",
        )

    def test_live_irrelevant_negative_control(self):
        domain="nist.gov"
        hits=ror_exact(domain)
        self.assertEqual(len(hits),1)
        url="https://www.nist.gov/pqc"
        out=self.m.verify(
            "Assess volcanic sulfur isotope fractionation in mantle magma plumes",
            {"url":url},
            {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":url,"final_host":"www.nist.gov"},
            {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":domain},
            timeout=20,
        )
        self.assertNotEqual(out.get("status"),"FIRST_PARTY_RELEVANT_SOURCE_VERIFIED",out)
        self.assertEqual(out.get("objective_relevance_status"),"UNVERIFIED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
