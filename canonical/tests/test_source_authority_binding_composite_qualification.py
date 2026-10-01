#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, subprocess, sys, unittest, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"
EXPECTED={
 "source_candidate_provenance_verify.py":"1dc26e68d18010b66211d1d83f7b2024c8ad1fcf",
 "source_authority_binding_ror.py":"9396ff7169b274af9bbfbe736e004587631e3b05",
 "source_authority_binding_wikidata.py":"a293ffae6e9f62b6087aab804718bc30a92b2105",
 "source_authority_binding_composite.py":"e5e760c804b4648d1e63979bc812314c5902e342",
}
UA="ProjectBrain-Independent-AuthorityComposite-Oracle/1.0"

def load(name):
    p=BC/(name+".py")
    s=importlib.util.spec_from_file_location("q_"+name,p)
    m=importlib.util.module_from_spec(s)
    sys.modules[s.name]=m
    s.loader.exec_module(m)
    return m

def fetch_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read(3_000_000).decode("utf-8","replace")),r.geturl()

def independent_ror(domain):
    u="https://api.ror.org/v2/organizations?"+urllib.parse.urlencode({"query.advanced":f'domains:"{domain}"'})
    data,final=fetch_json(u)
    assert (urllib.parse.urlsplit(final).hostname or "").lower()=="api.ror.org"
    exact=[]
    for rec in data.get("items") or []:
        if str(rec.get("status") or "").lower()!="active": continue
        ds=[str(x or "").lower().strip(".").removeprefix("www.") for x in rec.get("domains") or []]
        if domain in ds: exact.append(rec)
    return exact

def independent_p856(label,wanted_host):
    q="https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({
      "action":"wbsearchentities","search":label,"language":"en","format":"json","limit":8
    })
    data,_=fetch_json(q)
    wanted=wanted_host.lower().strip(".").removeprefix("www.")
    for item in data.get("search") or []:
        qid=str(item.get("id") or "")
        if not qid.startswith("Q"): continue
        ent,_=fetch_json("https://www.wikidata.org/wiki/Special:EntityData/"+qid+".json")
        obj=(ent.get("entities") or {}).get(qid) or {}
        for claim in ((obj.get("claims") or {}).get("P856") or []):
            try: raw=claim["mainsnak"]["datavalue"]["value"]
            except Exception: continue
            host=(urllib.parse.urlsplit(raw).hostname or "").lower().strip(".").removeprefix("www.")
            if host==wanted or host.endswith("."+wanted) or wanted.endswith("."+host):
                return {"qid":qid,"host":host,"url":raw}
    return None

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prov=load("source_candidate_provenance_verify")
        cls.comp=load("source_authority_binding_composite")

    def test_exact_candidate_blobs(self):
        for name,want in EXPECTED.items():
            got=subprocess.check_output(["git","hash-object",str(BC/name)],text=True).strip()
            self.assertEqual(got,want,(name,got,want))

    def _bind_live(self,candidate):
        p=self.prov.verify(candidate,timeout=20)
        self.assertIn(p.get("status"),{"RETRIEVAL_PROVENANCE_VERIFIED","BIBLIOGRAPHIC_PROVENANCE_VERIFIED"},p)
        return p,self.comp.bind_verified_candidate(candidate,p,timeout=20)

    def test_live_python_p856_path_matches_independent_registry(self):
        candidate={"url":"https://www.python.org/","title":"Welcome to Python.org"}
        provenance,out=self._bind_live(candidate)
        self.assertEqual(out.get("status"),"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertIn("WIKIDATA_P856_OFFICIAL_WEBSITE",out.get("verification_methods") or [],out)
        oracle=independent_p856("Python","python.org")
        self.assertIsNotNone(oracle)
        self.assertEqual(out.get("primary_source_status"),"UNVERIFIED")
        self.assertEqual(out.get("relevance_status"),"UNVERIFIED")
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED")
        self.assertEqual(out.get("model_dependency_count"),0)
        self.assertEqual(out.get("incremental_spend_usd"),0)

    def test_live_harvard_ror_path_matches_independent_registry(self):
        candidate={"url":"https://www.harvard.edu/","title":"Harvard University"}
        provenance,out=self._bind_live(candidate)
        self.assertEqual(out.get("status"),"AUTHORITY_IDENTITY_VERIFIED",out)
        self.assertIn("ROR_V2_EXACT_ACTIVE_DOMAIN",out.get("verification_methods") or [],out)
        self.assertEqual(len(independent_ror("harvard.edu")),1)
        self.assertEqual(out.get("primary_source_status"),"UNVERIFIED")
        self.assertEqual(out.get("relevance_status"),"UNVERIFIED")
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED")

    def test_identity_binding_never_upgrades_evidence_semantics(self):
        # example.com is intentionally a documentation entity and has a real
        # Wikidata P856 binding. Identity may therefore verify, but it must not
        # silently become research relevance, primary-source status, or evidence.
        candidate={"url":"https://example.com/","title":"Example Domain"}
        provenance,out=self._bind_live(candidate)
        self.assertIn(out.get("status"),{"AUTHORITY_IDENTITY_VERIFIED","AUTHORITY_UNRESOLVED"},out)
        self.assertEqual(out.get("primary_source_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("relevance_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)

    def test_unverified_provenance_never_binds(self):
        out=self.comp.bind_verified_candidate({"url":"https://www.python.org/"},{"status":"UNVERIFIED"})
        self.assertEqual(out.get("status"),"AUTHORITY_UNRESOLVED",out)
        self.assertEqual(out.get("reason"),"QUALIFIED_PROVENANCE_REQUIRED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
