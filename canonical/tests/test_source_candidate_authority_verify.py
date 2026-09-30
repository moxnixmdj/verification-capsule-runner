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

class SourceAuthorityVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_safe_url_rejects_local(self):
        self.assertIsNone(self.m._safe_url("file:///tmp/a"))
        self.assertIsNone(self.m._safe_url("http://localhost/a"))
        self.assertEqual(self.m._safe_url("https://example.org/a"),"https://example.org/a")

    def test_crossref_verifies_identity_never_authority(self):
        candidate={
            "url":"https://doi.org/10.1000/test","host":"doi.org",
            "title":"A Test Paper","publisher":"Example Publisher","doi":"10.1000/test",
        }
        payload={"message":{"DOI":"10.1000/test","title":["A Test Paper"],"publisher":"Example Publisher","type":"journal-article"}}
        with mock.patch.object(self.m,"_fetch_json",return_value=(payload,"https://api.crossref.org/works/10.1000%2Ftest",200)):
            out=self.m._crossref_identity(candidate,10)
        self.assertTrue(out["identity_verified"])
        self.assertFalse(out["authority_verified"])
        self.assertEqual(out["authority_scope"],"NONE")
        self.assertEqual(out["primary_evidence_status"],"NOT_VERIFIED")

    def test_doi_infrastructure_host_cannot_be_authority(self):
        candidate={"url":"https://doi.org/10.1000/test","host":"doi.org","title":"Python study","doi":"10.1000/test"}
        out=self.m._wikidata_official_site_authority(candidate,"Python official documentation",10)
        self.assertFalse(out["authority_verified"])
        self.assertEqual(out["reason"],"GENERIC_INFRASTRUCTURE_HOST_NOT_SOURCE_AUTHORITY")

    def test_relevant_entity_p856_can_verify_official_site_identity(self):
        candidate={"url":"https://docs.python.org/3/","host":"docs.python.org","title":"Python documentation"}
        search={"search":[{"id":"Q28865","label":"Python","description":"programming language","match":{"text":"Python"}}]}
        entity={"entities":{"Q28865":{"claims":{"P856":[{"mainsnak":{"datavalue":{"value":"https://www.python.org/"}}}]}}}}
        def fake(url,timeout=20,max_bytes=2500000):
            if "wbsearchentities" in url:
                return search,url,200
            if "Special:EntityData" in url:
                return entity,url,200
            raise AssertionError(url)
        with mock.patch.object(self.m,"_fetch_json",side_effect=fake):
            out=self.m._wikidata_official_site_authority(candidate,"Python programming language official documentation",10)
        self.assertTrue(out["identity_verified"])
        self.assertTrue(out["authority_verified"])
        self.assertEqual(out["authority_scope"],"ENTITY_OFFICIAL_WEBSITE_IDENTITY")
        self.assertEqual(out["primary_evidence_status"],"NOT_VERIFIED")

    def test_irrelevant_entity_cannot_create_authority(self):
        candidate={"url":"https://docs.python.org/3/","host":"docs.python.org","title":"Python documentation"}
        search={"search":[{"id":"Q999","label":"Unrelated entity","description":"something else","match":{"text":"unrelated"}}]}
        entity={"entities":{"Q999":{"claims":{"P856":[{"mainsnak":{"datavalue":{"value":"https://www.python.org/"}}}]}}}}
        def fake(url,timeout=20,max_bytes=2500000):
            if "wbsearchentities" in url: return search,url,200
            if "Special:EntityData" in url: return entity,url,200
            raise AssertionError(url)
        with mock.patch.object(self.m,"_fetch_json",side_effect=fake):
            out=self.m._wikidata_official_site_authority(candidate,"Python programming language official documentation",10)
        self.assertFalse(out["authority_verified"])

    def test_identity_only_discovery_stays_authority_unresolved(self):
        discovery={
            "objective":"lithium ion battery aging experimental study",
            "candidates":[{"url":"https://doi.org/10.1000/test","host":"doi.org","title":"Lithium battery aging","publisher":"Example","doi":"10.1000/test"}],
        }
        identity={
            "status":"SOURCE_IDENTITY_VERIFIED_AUTHORITY_UNRESOLVED",
            "candidate":discovery["candidates"][0],
            "identity_verified":True,
            "authority_verified":False,
            "primary_evidence_status":"NOT_VERIFIED",
            "evidence_sufficiency_status":"NOT_VERIFIED",
        }
        with mock.patch.object(self.m,"verify_candidate",return_value=identity):
            out=self.m.verify_discovery(discovery)
        self.assertEqual(out["status"],"SOURCE_IDENTITIES_AVAILABLE_AUTHORITY_UNRESOLVED")
        self.assertEqual(out["authority_verified_count"],0)
        self.assertEqual(out["crossref_authority_policy"],"BIBLIOGRAPHIC_IDENTITY_ONLY_NEVER_AUTHORITY")
        self.assertEqual(out["primary_evidence_verification"],"NOT_PERFORMED")

if __name__=="__main__":
    unittest.main(verbosity=2)
