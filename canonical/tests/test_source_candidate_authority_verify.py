#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/source_candidate_authority_verify.py"

def load():
    spec=importlib.util.spec_from_file_location("authority_verify",PATH)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class AuthorityIdentityVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_safe_url_rejects_local(self):
        self.assertIsNone(self.m._safe_url("file:///tmp/a"))
        self.assertIsNone(self.m._safe_url("http://localhost/a"))
        self.assertEqual(self.m._safe_url("https://example.org/a"),"https://example.org/a")

    def test_crossref_registry_match_is_narrow(self):
        candidate={
            "url":"https://doi.org/10.1000/test",
            "host":"doi.org",
            "title":"A Test Paper",
            "publisher":"Example Publisher",
            "doi":"10.1000/test",
        }
        payload={"message":{"DOI":"10.1000/test","title":["A Test Paper"],"publisher":"Example Publisher","type":"journal-article"}}
        with mock.patch.object(self.m,"_fetch_json",return_value=(payload,"https://api.crossref.org/works/10.1000%2Ftest",200)):
            out=self.m._crossref_verify(candidate,10)
        self.assertTrue(out["verified"])
        self.assertEqual(out["reason"],"REGISTRY_BIBLIOGRAPHIC_IDENTITY_MATCH")
        self.assertEqual(out["primary_evidence_status"],"NOT_VERIFIED")

    def test_wikidata_p856_host_match(self):
        candidate={"url":"https://docs.python.org/3/library/urllib.request.html","host":"docs.python.org","title":"urllib.request"}
        search={"search":[{"id":"Q28865","label":"Python"}]}
        entity={"entities":{"Q28865":{"claims":{"P856":[{"mainsnak":{"datavalue":{"value":"https://www.python.org/"}}}]}}}}
        def fake(url,timeout=20,max_bytes=2500000):
            if "wbsearchentities" in url:
                return search,url,200
            if "Special:EntityData" in url:
                return entity,url,200
            raise AssertionError(url)
        with mock.patch.object(self.m,"_fetch_json",side_effect=fake):
            out=self.m._wikidata_official_site_verify(candidate,"Python urllib request official documentation",10)
        self.assertTrue(out["verified"])
        self.assertEqual(out["signal"],"WIKIDATA_P856_OFFICIAL_WEBSITE")
        self.assertEqual(out["primary_evidence_status"],"NOT_VERIFIED")

    def test_relevance_does_not_create_authority(self):
        candidate={"url":"https://example.org/sqlite","host":"example.org","title":"SQLite backup consistency"}
        rel=self.m._relevance("Determine SQLite backup consistency",candidate)
        self.assertEqual(rel["status"],"OBJECTIVE_TERM_CORROBORATED")
        unresolved={
            "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
            "verified":False,
            "reason":"NO_MATCH",
        }
        with mock.patch.object(self.m,"_crossref_verify",return_value=None), mock.patch.object(self.m,"_wikidata_official_site_verify",return_value=unresolved):
            out=self.m.verify_candidate("Determine SQLite backup consistency",candidate)
        self.assertEqual(out["status"],"AUTHORITY_IDENTITY_UNRESOLVED")
        self.assertFalse(out["authority_identity_verified"])

    def test_discovery_preserves_primary_evidence_boundary(self):
        discovery={
            "objective":"Assess Python urllib request documentation",
            "candidates":[{"url":"https://docs.python.org/3/","host":"docs.python.org","title":"Python docs"}],
        }
        verified={
            "status":"AUTHORITY_IDENTITY_CANDIDATE_VERIFIED",
            "candidate":discovery["candidates"][0],
            "authority_identity_verified":True,
            "primary_evidence_status":"NOT_VERIFIED",
            "evidence_sufficiency_status":"NOT_VERIFIED",
        }
        with mock.patch.object(self.m,"verify_candidate",return_value=verified):
            out=self.m.verify_discovery(discovery)
        self.assertEqual(out["status"],"AUTHORITY_IDENTITY_CANDIDATES_AVAILABLE")
        self.assertEqual(out["primary_evidence_verification"],"NOT_PERFORMED")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
