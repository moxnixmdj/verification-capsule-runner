#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import importlib.util
import pathlib
import urllib.request
import unittest
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[2]
CAP=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    path=CAP/(name+".py")
    spec=importlib.util.spec_from_file_location("independent_"+name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class IndependentVisibleText(HTMLParser):
    """Independent broad visible-text oracle.

    This intentionally does not reproduce the producer's block/container tag
    list or segmentation. It proves emitted evidence text is genuinely present
    in an independently re-fetched visible page while producer-internal offsets
    and IDs are checked for arithmetic/hash consistency.
    """
    SUPPRESS={"script","style","noscript","svg"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in self.SUPPRESS:
            self.suppress+=1
    def handle_endtag(self,tag):
        if tag.lower() in self.SUPPRESS and self.suppress:
            self.suppress-=1
    def handle_data(self,data):
        if self.suppress:
            return
        text=" ".join(str(data or "").split())
        if text:
            self.parts.append(text)

def independent_visible(url):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":"ProjectBrain-Independent-Generic-Evidence-Oracle/2.0",
            "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(req,timeout=25) as response:
        raw=response.read(2_000_000)
        final=response.geturl()
        ctype=str(response.headers.get("Content-Type") or "")
    decoded=raw.decode("utf-8","replace")
    if "html" in ctype.lower() or "<html" in decoded[:2000].lower():
        parser=IndependentVisibleText()
        parser.feed(decoded)
        visible=html.unescape(" ".join(parser.parts))
    else:
        visible=decoded
    return final," ".join(visible.split())

def norm(text):
    return " ".join(str(text or "").split())

class GenericLiveQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor=load("objective_evidence_unit_extract")
        cls.ranker=load("objective_relevance_bm25")
        cls.provenance=load("source_candidate_provenance_verify")

    def _case(self,target,distractor,objective):
        candidates=[distractor,target]
        rank=self.ranker.rank(objective,candidates)
        self.assertEqual(rank.get("status"),"LEXICAL_RELEVANCE_RANKED",rank)
        self.assertTrue(rank.get("output_verified"),rank)
        self.assertEqual(rank.get("top_candidate_original_index"),1,rank)

        prov=self.provenance.verify(target,timeout=25)
        self.assertEqual(prov.get("status"),"RETRIEVAL_PROVENANCE_VERIFIED",prov)
        self.assertEqual(prov.get("candidate_url"),target["url"],prov)

        out=self.extractor.extract(
            objective,target,prov,rank,timeout=25,max_units=8
        )
        self.assertEqual(out.get("status"),"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertEqual(out.get("evidence_extraction_status"),"VERIFIED",out)
        self.assertGreater(out.get("evidence_unit_count",0),0,out)
        self.assertEqual(out.get("claim_relation_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("evidence_sufficiency_status"),"UNVERIFIED",out)
        self.assertEqual(out.get("model_dependency_count"),0,out)
        self.assertEqual(out.get("incremental_spend_usd"),0,out)
        self.assertEqual(len(out.get("page_raw_sha256") or ""),64,out)
        self.assertEqual(len(out.get("visible_text_sha256") or ""),64,out)

        final,independent=independent_visible(prov["final_url"])
        self.assertEqual(final,prov["final_url"])
        self.assertTrue(independent)

        seen_ids=set()
        for unit in out["evidence_units"]:
            self.assertIn(norm(unit["text"]),independent,unit)
            self.assertEqual(
                hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
                unit["text_sha256"],
                unit,
            )
            self.assertGreaterEqual(unit["visible_text_start"],0,unit)
            self.assertGreater(unit["visible_text_end"],unit["visible_text_start"],unit)
            self.assertEqual(
                unit["visible_text_end"]-unit["visible_text_start"],
                len(unit["text"]),
                unit,
            )
            self.assertLessEqual(unit["visible_text_end"],out["visible_text_length"],unit)
            expected_id=hashlib.sha256(
                f'{out["page_raw_sha256"]}:{unit["visible_text_start"]}:{unit["visible_text_end"]}:{unit["text_sha256"]}'.encode("utf-8")
            ).hexdigest()
            self.assertEqual(expected_id,unit["evidence_unit_id"],unit)
            self.assertNotIn(unit["evidence_unit_id"],seen_ids,unit)
            seen_ids.add(unit["evidence_unit_id"])
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),2,unit)
        return out

    def test_sqlite_wal_without_ror_admission(self):
        self._case(
            {
                "url":"https://www.sqlite.org/wal.html",
                "title":"SQLite Write-Ahead Logging",
                "snippet":"WAL write ahead logging checkpoint database concurrency behavior",
            },
            {
                "url":"https://example.org/campus",
                "title":"Campus office directory",
                "snippet":"Administrative contacts and cafeteria hours",
            },
            "Assess SQLite WAL write ahead logging checkpoint behavior",
        )

    def test_python_hashlib_without_ror_admission(self):
        self._case(
            {
                "url":"https://docs.python.org/3/library/hashlib.html",
                "title":"hashlib secure hashes and message digests",
                "snippet":"Python hashlib sha256 secure hash digest algorithms",
            },
            {
                "url":"https://example.org/weather",
                "title":"Weather archive",
                "snippet":"Rainfall temperature forecast observations",
            },
            "Assess Python hashlib sha256 secure hash digest algorithms",
        )

    def test_non_selected_candidate_fails_before_network(self):
        objective="Assess SQLite WAL checkpoint behavior"
        target={"url":"https://www.sqlite.org/wal.html","title":"SQLite WAL","snippet":"checkpoint behavior"}
        other={"url":"https://example.org/other","title":"Other","snippet":"irrelevant"}
        rank=self.ranker.rank(objective,[target,other])
        prov={
            "status":"RETRIEVAL_PROVENANCE_VERIFIED",
            "candidate_url":other["url"],
            "final_url":other["url"],
        }
        calls=[]
        out=self.extractor.extract(
            objective,other,prov,rank,
            fetch=lambda *args:calls.append(args)
        )
        self.assertEqual(out.get("reason"),"CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT",out)
        self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main(verbosity=2)
