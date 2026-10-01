#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, urllib.parse, urllib.request, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_ror.py"
EXPECTED_BLOB="9396ff7169b274af9bbfbe736e004587631e3b05"

def load():
    s=importlib.util.spec_from_file_location("ror_candidate",P)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def independent_ror(domain, timeout=20):
    url="https://api.ror.org/v2/organizations?"+urllib.parse.urlencode({"query.advanced":f'domains:"{domain}"'})
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-ROR-Oracle/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=json.loads(r.read(3000000).decode("utf-8","replace"))
        final=r.geturl()
    if (urllib.parse.urlsplit(final).hostname or "").lower()!="api.ror.org":
        raise AssertionError("ROR oracle redirected outside api.ror.org")
    exact=[]
    for rec in data.get("items") or []:
        if str(rec.get("status") or "").lower()!="active":
            continue
        domains=[]
        for raw in rec.get("domains") or []:
            h=str(raw or "").lower().strip(".")
            if h.startswith("www."): h=h[4:]
            domains.append(h)
        if domain in domains:
            exact.append(rec)
    return exact

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_exact_candidate_blob(self):
        import subprocess
        got=subprocess.check_output(["git","hash-object",str(P)],text=True).strip()
        self.assertEqual(got,EXPECTED_BLOB)

    def test_live_cross_domain_exact_bindings_match_independent_oracle(self):
        positives=[]
        for domain in ("harvard.edu","nasa.gov"):
            oracle=independent_ror(domain)
            if len(oracle)==1:
                out=self.m.bind_candidate({"url":"https://"+domain+"/"},timeout=20)
                self.assertEqual(out.get("status"),"AUTHORITY_IDENTITY_VERIFIED",out)
                self.assertEqual(out.get("matched_domain"),domain,out)
                self.assertEqual(out.get("primary_source_status"),"UNVERIFIED",out)
                self.assertEqual(out.get("relevance_status"),"UNVERIFIED",out)
                self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)
                self.assertEqual(out.get("model_dependency_count"),0,out)
                self.assertEqual(out.get("incremental_spend_usd"),0,out)
                positives.append(domain)
        self.assertGreaterEqual(len(positives),1,"No independent live ROR exact-domain positive remained available")

    def test_unsupported_domain_fails_closed(self):
        out=self.m.bind_candidate({"url":"https://example.com/"},timeout=20)
        self.assertNotEqual(out.get("status"),"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertEqual(out.get("authority_status"),"UNVERIFIED",out)

    def test_ambiguity_is_rejected(self):
        old=self.m._fetch_ror
        try:
            self.m._fetch_ror=lambda domain,timeout=20: ({
                "number_of_results":2,
                "items":[
                    {"id":"https://ror.org/01","status":"active","domains":[domain],"names":[{"value":"A","types":["ror_display"]}]},
                    {"id":"https://ror.org/02","status":"active","domains":[domain],"names":[{"value":"B","types":["ror_display"]}]},
                ]
            },"https://api.ror.org/v2/organizations",200)
            out=self.m.bind_candidate({"url":"https://ambiguous.example.org/"},timeout=5)
            self.assertEqual(out.get("status"),"AUTHORITY_AMBIGUOUS",out)
            self.assertEqual(out.get("authority_status"),"UNVERIFIED",out)
        finally:
            self.m._fetch_ror=old

if __name__=="__main__":
    unittest.main(verbosity=2)
