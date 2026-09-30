#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, re, subprocess, urllib.parse, urllib.request, unittest
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[2]
EXTRACTOR=ROOT/"canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"
RELEVANCE=ROOT/"canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py"

EXPECTED_EXTRACTOR_BLOB="58bdca4b1f1088757bcd0968b9931ce1dbb46e16"
EXPECTED_FRONTEND_BLOB="840fd3a665cc506e07203e1267e8ddd2d958b177"
EXPECTED_ASTRA_BLOB="83126296e2b44a3ab661595fdd266bc64dc7bf31"
EXPECTED_RELEVANCE_BLOB="6ff13c32704c0b3283c42a51f718e875110a13ca"
ROR="https://api.ror.org/v2/organizations"
UA="ProjectBrain-Independent-EvidenceExtraction-Oracle/1.0"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class VisibleOracle(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","svg"}:
            self.suppress+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","svg"} and self.suppress:
            self.suppress-=1
    def handle_data(self,data):
        if not self.suppress:
            text=" ".join(str(data or "").split())
            if text:
                self.parts.append(text)

def canon(value):
    return " ".join(str(value or "").split())

def norm_host(value):
    host=(urllib.parse.urlsplit(str(value)).hostname or str(value)).lower().strip(".")
    if host.startswith("www."):
        host=host[4:]
    return host

def fetch(url,timeout=25):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.2"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        raw=response.read(3_000_000)
        final=response.geturl()
        ctype=str(response.headers.get("Content-Type") or "")
        status=int(getattr(response,"status",200))
    return raw,final,ctype,status

def provenance(url):
    raw,final,ctype,status=fetch(url)
    return {
        "status":"RETRIEVAL_PROVENANCE_VERIFIED",
        "final_url":final,
        "final_host":norm_host(final),
        "http_status":status,
        "content_type":ctype,
        "raw_sha256":hashlib.sha256(raw).hexdigest(),
    }

def ror_exact(domain,timeout=20):
    url=ROR+"?"+urllib.parse.urlencode({"query.advanced":f'domains:"{domain}"'})
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        data=json.loads(response.read(3_000_000).decode("utf-8","replace"))
    hits=[]
    for record in data.get("items") or []:
        if str(record.get("status") or "").lower()!="active":
            continue
        domains=[]
        for item in record.get("domains") or []:
            value=str(item or "").lower().strip(".")
            if value.startswith("www."):
                value=value[4:]
            domains.append(value)
        if domain in domains:
            hits.append(record)
    return hits

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor=load(EXTRACTOR,"candidate_extractor")
        cls.relevance=load(RELEVANCE,"qualified_relevance")

    def test_exact_candidate_blobs(self):
        expected={
            EXTRACTOR:EXPECTED_EXTRACTOR_BLOB,
            ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py":EXPECTED_FRONTEND_BLOB,
            ROOT/"canonical/runtime/astra_runtime.py":EXPECTED_ASTRA_BLOB,
            RELEVANCE:EXPECTED_RELEVANCE_BLOB,
        }
        for path,blob in expected.items():
            got=subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
            self.assertEqual(got,blob,(path,got,blob))

    def _positive(self,domain,url,objective):
        prov=provenance(url)
        final_url=prov["final_url"]
        final_domain=norm_host(final_url)
        self.assertEqual(final_domain,domain,(final_url,final_domain,domain))

        hits=ror_exact(domain)
        self.assertEqual(len(hits),1,(domain,len(hits)))
        authority={
            "status":"AUTHORITY_IDENTITY_VERIFIED",
            "matched_domain":domain,
            "organization_name":next(
                (str(n.get("value")) for n in (hits[0].get("names") or []) if "ror_display" in (n.get("types") or [])),
                None,
            ),
        }
        relevance=self.relevance.verify(
            objective,
            {"url":final_url},
            prov,
            authority,
            timeout=20,
        )
        self.assertEqual(relevance.get("objective_relevance_status"),"VERIFIED",relevance)

        out=self.extractor.extract(
            objective,
            {"url":final_url},
            prov,
            relevance,
            timeout=20,
            max_units=6,
        )
        self.assertEqual(out.get("status"),"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertEqual(out.get("evidence_extraction_status"),"VERIFIED",out)
        self.assertGreaterEqual(out.get("evidence_unit_count",0),1,out)
        self.assertEqual(out.get("model_dependency_count"),0,out)
        self.assertEqual(out.get("incremental_spend_usd"),0,out)
        self.assertEqual(out.get("claim_relation_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)

        raw2,final2,ctype2,status2=fetch(final_url)
        self.assertEqual(norm_host(final2),domain)
        text=raw2.decode("utf-8","replace")
        parser=VisibleOracle()
        if "html" in ctype2.lower() or "<html" in text[:2000].lower():
            parser.feed(text)
            visible=canon(" ".join(parser.parts))
        else:
            visible=canon(text)
        visible_lower=visible.lower()
        for unit in out["evidence_units"]:
            unit_text=canon(unit["text"])
            self.assertIn(unit_text.lower(),visible_lower,(domain,unit_text[:120]))
            self.assertEqual(hashlib.sha256(unit_text.encode("utf-8")).hexdigest(),unit["text_sha256"])
            unit_lower=unit_text.lower()
            for token in unit["matched_objective_tokens"]:
                self.assertIn(token.lower(),unit_lower,(token,unit_text))
        return out

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

    def test_extractor_contract_has_no_authority_identity_parameter(self):
        import inspect
        params=list(inspect.signature(self.extractor.extract).parameters)
        self.assertEqual(params[:4],["objective","candidate","provenance","relevance"],params)
        self.assertNotIn("authority_identity",params)

if __name__=="__main__":
    unittest.main(verbosity=2)
