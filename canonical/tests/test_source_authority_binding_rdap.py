#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_rdap.py"
def load():
    s=importlib.util.spec_from_file_location("ab",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
class AuthorityBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()
    def test_host_extraction(self):
        self.assertEqual(self.m._candidate_host({"final_url":"https://docs.python.org/3/"}),"docs.python.org")
    def test_private_host_rejected(self):
        self.assertIsNone(self.m._candidate_host({"url":"http://localhost/x"}))
    def test_domain_fallback_is_generic(self):
        self.assertEqual(self.m._domain_candidates("docs.python.org"),["docs.python.org","python.org"])
    def test_entity_match_legal_suffix(self):
        self.assertTrue(self.m._entity_match("Example Research Foundation","Example Research Foundation, Inc."))
        self.assertFalse(self.m._entity_match("Example Research Foundation","Unrelated Foundation"))
    def test_missing_claim_fails_closed(self):
        x=self.m.verify({"url":"https://example.org/x"},"")
        self.assertEqual(x["status"],"UNVERIFIED")
        self.assertEqual(x["primary_source_status"],"UNVERIFIED")
    def test_synthetic_rdap_match_and_nonclaim_boundary(self):
        old=self.m._fetch_rdap
        try:
            self.m._fetch_rdap=lambda d,t: ({"ldhName":"example.org","entities":[{"roles":["registrant"],"vcardArray":["vcard",[
                ["version",{},"text","4.0"],["fn",{},"text","Example Research Foundation, Inc."]
            ]]}]},"https://registry.example/rdap/domain/example.org",200)
            x=self.m.verify({"url":"https://www.example.org/paper"},"Example Research Foundation")
            self.assertEqual(x["status"],"AUTHORITY_BINDING_VERIFIED",x)
            self.assertEqual(x["authority_status"],"VERIFIED_HOST_TO_ISSUING_ENTITY_BINDING")
            self.assertEqual(x["primary_source_status"],"UNVERIFIED")
            self.assertEqual(x["relevance_status"],"UNVERIFIED")
            self.assertEqual(x["evidence_sufficiency_status"],"UNVERIFIED")
        finally:
            self.m._fetch_rdap=old
    def test_synthetic_mismatch_fails_closed(self):
        old=self.m._fetch_rdap
        try:
            self.m._fetch_rdap=lambda d,t: ({"ldhName":"example.org","entities":[{"roles":["registrant"],"vcardArray":["vcard",[
                ["fn",{},"text","Different Organization"]
            ]]}]},"https://registry.example/rdap/domain/example.org",200)
            x=self.m.verify({"url":"https://example.org/x"},"Example Research Foundation")
            self.assertEqual(x["status"],"UNVERIFIED")
            self.assertEqual(x["reason"],"RDAP_REGISTRANT_ENTITY_MISMATCH")
        finally:
            self.m._fetch_rdap=old
if __name__=="__main__": unittest.main(verbosity=2)
