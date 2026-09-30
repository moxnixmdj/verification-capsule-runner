#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/official_primary_relevance_verify.py"

def load():
    spec=importlib.util.spec_from_file_location("official_primary_relevance_verify",P)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def provenance(url,host):
    return {
        "status":"RETRIEVAL_PROVENANCE_VERIFIED",
        "final_url":url,
        "final_host":host,
    }

def authority(candidate_host,official_host):
    return {
        "status":"AUTHORITY_IDENTITY_VERIFIED",
        "authority_status":"VERIFIED",
        "candidate_host":candidate_host,
        "official_host":official_host,
        "authority_claim_scope":"HOST_TO_DECLARED_OFFICIAL_WEBSITE_IDENTITY_ONLY",
    }

class OfficialPrimaryRelevanceVerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_official_python_technical_doc_and_relevant_objective_verifies(self):
        objective=(
            "Determine whether ordinary sequential summation in 64-bit binary "
            "floating-point arithmetic can yield materially less accurate results "
            "than a numerically stable summation strategy under severe cancellation."
        )
        candidate={
            "url":"https://docs.python.org/3/library/math.html",
            "host":"docs.python.org",
            "title":"math — Mathematical functions — Python documentation",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
        }
        page=(
            "math.fsum(iterable) Return an accurate floating-point sum of values. "
            "Avoids loss of precision by tracking multiple intermediate partial sums. "
            "The algorithm's accuracy depends on IEEE-754 arithmetic guarantees. "
            "Large magnitude inputs can mostly cancel each other out."
        )
        out=self.m.verify(
            objective,candidate,
            provenance(candidate["url"],candidate["host"]),
            authority(candidate["host"],"www.python.org"),
            fetch_text=lambda url,timeout: {
                "url":url,"final_url":url,"content_type":"text/html","text":page
            },
        )
        self.assertEqual(out["status"],"PRIMARY_RELEVANCE_VERIFIED",out)
        self.assertEqual(out["primary_source_status"],"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT")
        self.assertEqual(out["relevance_status"],"VERIFIED_DIRECT_OBJECTIVE_COVERAGE")
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED")
        self.assertGreaterEqual(out["relevance"]["matched_salient_count"],3)
        self.assertGreaterEqual(out["relevance"]["matched_adjacent_concept_count"],1)
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)

    def test_official_homepage_is_not_primary_technical_document(self):
        candidate={
            "url":"https://www.python.org/",
            "host":"www.python.org",
            "title":"Welcome to Python.org",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
        }
        out=self.m.verify(
            "Determine floating-point summation accuracy.",
            candidate,
            provenance(candidate["url"],candidate["host"]),
            authority(candidate["host"],"www.python.org"),
            fetch_text=lambda url,timeout: {
                "url":url,"final_url":url,"content_type":"text/html",
                "text":"Welcome to Python.org. Get started, download Python, community news."
            },
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")

    def test_unrelated_official_technical_doc_fails_relevance(self):
        candidate={
            "url":"https://docs.python.org/3/library/socket.html",
            "host":"docs.python.org",
            "title":"socket — Low-level networking interface",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
        }
        out=self.m.verify(
            "Determine whether floating-point summation under severe cancellation loses accuracy.",
            candidate,
            provenance(candidate["url"],candidate["host"]),
            authority(candidate["host"],"www.python.org"),
            fetch_text=lambda url,timeout: {
                "url":url,"final_url":url,"content_type":"text/html",
                "text":"Socket programming provides access to BSD network sockets, addresses, ports, protocols, and connections."
            },
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["primary_source_status"],"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT",out)
        self.assertEqual(out["relevance_status"],"UNVERIFIED",out)

    def test_authority_is_required(self):
        candidate={
            "url":"https://docs.python.org/3/library/math.html",
            "host":"docs.python.org",
            "title":"math — Mathematical functions — Python documentation",
        }
        out=self.m.verify(
            "Determine floating-point summation accuracy.",
            candidate,
            provenance(candidate["url"],candidate["host"]),
            {"status":"AUTHORITY_UNRESOLVED","authority_status":"UNVERIFIED"},
            fetch_text=lambda url,timeout: {"url":url,"final_url":url,"content_type":"text/html","text":"floating point sum"},
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"VERIFIED_AUTHORITY_BINDING_REQUIRED")

    def test_live_retrieval_provenance_is_required(self):
        candidate={
            "url":"https://docs.python.org/3/library/math.html",
            "host":"docs.python.org",
            "title":"math — Mathematical functions — Python documentation",
        }
        out=self.m.verify(
            "Determine floating-point summation accuracy.",
            candidate,
            {"status":"UNVERIFIED"},
            authority(candidate["host"],"www.python.org"),
            fetch_text=lambda url,timeout: {"url":url,"final_url":url,"content_type":"text/html","text":"floating point sum"},
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"LIVE_RETRIEVAL_PROVENANCE_REQUIRED")

    def test_authority_site_mismatch_fails_closed(self):
        candidate={
            "url":"https://docs.python.org/3/library/math.html",
            "host":"docs.python.org",
            "title":"math — Mathematical functions — Python documentation",
        }
        out=self.m.verify(
            "Determine floating-point summation accuracy.",
            candidate,
            provenance(candidate["url"],candidate["host"]),
            authority(candidate["host"],"example.org"),
            fetch_text=lambda url,timeout: {"url":url,"final_url":url,"content_type":"text/html","text":"floating point sum"},
        )
        self.assertEqual(out["status"],"UNVERIFIED",out)
        self.assertEqual(out["reason"],"AUTHORITY_HOST_RELATION_MISMATCH")

    def test_w3c_specification_class_is_accepted_when_relevant(self):
        objective="Determine the normative requirements for accessible web content under WCAG 2.2."
        candidate={
            "url":"https://www.w3.org/TR/WCAG22/",
            "host":"www.w3.org",
            "title":"Web Content Accessibility Guidelines (WCAG) 2.2",
            "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
        }
        page=(
            "Web Content Accessibility Guidelines WCAG 2.2 covers a wide range of recommendations "
            "for making web content more accessible. Conformance requirements and success criteria "
            "are normative requirements for accessible web content."
        )
        out=self.m.verify(
            objective,candidate,
            provenance(candidate["url"],candidate["host"]),
            authority(candidate["host"],"www.w3.org"),
            fetch_text=lambda url,timeout: {"url":url,"final_url":url,"content_type":"text/html","text":page},
        )
        self.assertEqual(out["status"],"PRIMARY_RELEVANCE_VERIFIED",out)
        self.assertEqual(out["evidence_sufficiency_status"],"UNVERIFIED")

if __name__=="__main__":
    unittest.main(verbosity=2)
