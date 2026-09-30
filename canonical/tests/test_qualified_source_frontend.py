#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/qualified_source_frontend.py"

def load():
    spec=importlib.util.spec_from_file_location("qualified_source_frontend",P)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_LOAD_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def decomposition(objective):
    return {
        "status":"DECOMPOSED",
        "objective":objective,
        "question_shape":"OPEN_RESEARCH_ASSESSMENT",
        "roles":[
            {"index":0,"role":"SOURCE_DISCOVERY","status":"REQUIRES_GROUNDING"},
            {"index":1,"role":"EVIDENCE_ACQUISITION","status":"REQUIRES_GROUNDING"},
        ],
    }

def candidate(url,title="Official technical reference"):
    from urllib.parse import urlsplit
    return {
        "url":url,
        "host":(urlsplit(url).hostname or "").lower(),
        "title":title,
        "source_class":"OPEN_WEB_SEARCH_CANDIDATE",
        "rank":0,
    }

class QualifiedSourceFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_full_gate_exposes_only_primary_relevant_authority_bound_sources(self):
        objective="Determine the normative requirements for accessible web content under WCAG 2.2."
        good=candidate("https://www.w3.org/TR/WCAG22/","Web Content Accessibility Guidelines (WCAG) 2.2")
        bad=candidate("https://www.w3.org/TR/css-color-4/","CSS Color Module Level 4")

        def discover(goal,limit=12,timeout=15):
            return {"status":"CANDIDATES_DISCOVERED","objective":goal,"candidates":[good,bad]}

        def provenance(c,timeout=15):
            return {
                "status":"RETRIEVAL_PROVENANCE_VERIFIED",
                "final_url":c["url"],"final_host":c["host"],
            }

        def authority(c,timeout=20):
            return {
                "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
                "candidate_host":c["host"],"official_host":"www.w3.org",
            }

        def primary(goal,c,p,a,timeout=20):
            if "WCAG" in c["title"]:
                return {
                    "status":"PRIMARY_RELEVANCE_VERIFIED",
                    "primary_source_status":"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT",
                    "relevance_status":"VERIFIED_DIRECT_OBJECTIVE_COVERAGE",
                    "evidence_sufficiency_status":"UNVERIFIED",
                }
            return {
                "status":"UNVERIFIED",
                "primary_source_status":"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT",
                "relevance_status":"UNVERIFIED",
                "evidence_sufficiency_status":"UNVERIFIED",
            }

        out=self.m.run(
            objective,decomposition(objective),
            discovery_fn=discover,provenance_fn=provenance,
            authority_fn=authority,primary_relevance_fn=primary,
        )
        self.assertEqual(out["status"],"QUALIFIED_SOURCE_AVAILABLE",out)
        self.assertEqual(out["qualified_source_count"],1,out)
        self.assertEqual(out["qualified_sources"][0]["candidate"]["url"],good["url"])
        self.assertEqual(out["evidence_sufficiency_verification"],"NOT_PERFORMED")
        self.assertEqual(out["next_required_capability"],"MODEL_INDEPENDENT_EVIDENCE_ACQUISITION_FROM_QUALIFIED_SOURCE")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["incremental_spend_usd"],0)

    def test_accepts_existing_qualified_ddgs_discovery_schema(self):
        objective="Assess the normative requirements for accessible web content under WCAG 2.2."
        good=candidate("https://www.w3.org/TR/WCAG22/","Web Content Accessibility Guidelines (WCAG) 2.2")

        def discover(goal,limit=12,timeout=15):
            return {
                "status":"SOURCE_CANDIDATES_DISCOVERED",
                "objective":goal,
                "candidates":[good],
                "model_dependency_count":0,
                "incremental_spend_usd":0,
            }

        def provenance(c,timeout=15):
            return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":c["url"],"final_host":c["host"]}

        def authority(c,timeout=20):
            return {
                "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
                "candidate_host":c["host"],"official_host":"www.w3.org",
            }

        def primary(goal,c,p,a,timeout=20):
            return {
                "status":"PRIMARY_RELEVANCE_VERIFIED",
                "primary_source_status":"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT",
                "relevance_status":"VERIFIED_DIRECT_OBJECTIVE_COVERAGE",
                "evidence_sufficiency_status":"UNVERIFIED",
            }

        out=self.m.run(
            objective,decomposition(objective),
            discovery_fn=discover,provenance_fn=provenance,
            authority_fn=authority,primary_relevance_fn=primary,
        )
        self.assertEqual(out["status"],"QUALIFIED_SOURCE_AVAILABLE",out)
        self.assertEqual(out["qualified_source_count"],1,out)

    def test_bibliographic_identity_does_not_skip_live_retrieval_gate(self):
        objective="Assess a technical claim."
        c=candidate("https://doi.org/10.0000/example","Example paper")
        called={"authority":0,"primary":0}
        def discover(goal,limit=12,timeout=15):
            return {"status":"CANDIDATES_DISCOVERED","objective":goal,"candidates":[c]}
        def provenance(x,timeout=15):
            return {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","doi":"10.0000/example"}
        def authority(x,timeout=20):
            called["authority"]+=1
            return {"status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED"}
        def primary(*args,**kwargs):
            called["primary"]+=1
            return {"status":"PRIMARY_RELEVANCE_VERIFIED"}

        out=self.m.run(
            objective,decomposition(objective),
            discovery_fn=discover,provenance_fn=provenance,
            authority_fn=authority,primary_relevance_fn=primary,
        )
        self.assertEqual(out["status"],"SOURCE_LIVE_RETRIEVAL_BLOCKED",out)
        self.assertEqual(called,{"authority":0,"primary":0})

    def test_authority_failure_blocks_primary_relevance(self):
        objective="Assess a technical claim."
        c=candidate("https://example.org/docs/spec","Example specification")
        called={"primary":0}
        def discover(goal,limit=12,timeout=15):
            return {"status":"CANDIDATES_DISCOVERED","objective":goal,"candidates":[c]}
        def provenance(x,timeout=15):
            return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":x["url"],"final_host":x["host"]}
        def authority(x,timeout=20):
            return {"status":"AUTHORITY_UNRESOLVED","authority_status":"UNVERIFIED"}
        def primary(*args,**kwargs):
            called["primary"]+=1
            return {"status":"PRIMARY_RELEVANCE_VERIFIED"}

        out=self.m.run(
            objective,decomposition(objective),
            discovery_fn=discover,provenance_fn=provenance,
            authority_fn=authority,primary_relevance_fn=primary,
        )
        self.assertEqual(out["status"],"SOURCE_AUTHORITY_BLOCKED",out)
        self.assertEqual(called["primary"],0)

    def test_primary_or_relevance_failure_keeps_evidence_acquisition_blocked(self):
        objective="Assess a technical claim."
        c=candidate("https://example.org/docs/spec","Example specification")
        def discover(goal,limit=12,timeout=15):
            return {"status":"CANDIDATES_DISCOVERED","objective":goal,"candidates":[c]}
        def provenance(x,timeout=15):
            return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":x["url"],"final_host":x["host"]}
        def authority(x,timeout=20):
            return {
                "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
                "candidate_host":x["host"],"official_host":x["host"],
            }
        def primary(goal,x,p,a,timeout=20):
            return {
                "status":"UNVERIFIED",
                "primary_source_status":"VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT",
                "relevance_status":"UNVERIFIED",
                "evidence_sufficiency_status":"UNVERIFIED",
            }

        out=self.m.run(
            objective,decomposition(objective),
            discovery_fn=discover,provenance_fn=provenance,
            authority_fn=authority,primary_relevance_fn=primary,
        )
        self.assertEqual(out["status"],"SOURCE_PRIMARY_RELEVANCE_BLOCKED",out)
        self.assertEqual(out["qualified_source_count"],0)
        self.assertEqual(out["role_progress"]["EVIDENCE_ACQUISITION"],"BLOCKED")

if __name__=="__main__":
    unittest.main(verbosity=2)
