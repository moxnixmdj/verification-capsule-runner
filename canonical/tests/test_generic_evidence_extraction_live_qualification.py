#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import importlib.util
import pathlib
import re
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

class Blocks(HTMLParser):
    BLOCK={"h1","h2","h3","h4","h5","h6","p","li","dt","dd","blockquote","td","th","pre","main","article","section","div"}
    SUPPRESS={"script","style","noscript","svg","nav","footer","header","form"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0
        self.stack=[]
        self.blocks=[]
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag in self.SUPPRESS:self.suppress+=1
        if self.suppress:return
        if tag in self.BLOCK:self.stack.append([tag,[]])
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in self.SUPPRESS:
            if self.suppress:self.suppress-=1
            return
        if self.suppress or tag not in self.BLOCK or not self.stack:return
        idx=None
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                idx=i;break
        if idx is None:return
        _,parts=self.stack.pop(idx)
        text=" ".join(" ".join(parts).split())
        if text:self.blocks.append(text)
    def handle_data(self,data):
        if self.suppress or not self.stack:return
        text=" ".join(str(data or "").split())
        if text:
            for frame in self.stack:frame[1].append(text)

def split_long(text,max_chars=900):
    text=" ".join(str(text or "").split())
    if not text:return []
    if len(text)<=max_chars:return [text]
    sentences=[" ".join(x.split()) for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text) if " ".join(x.split())]
    if len(sentences)<=1:
        return [text[i:i+max_chars].strip() for i in range(0,len(text),max_chars) if text[i:i+max_chars].strip()]
    out=[];buf=""
    for sentence in sentences:
        candidate=(buf+" "+sentence).strip() if buf else sentence
        if buf and len(candidate)>max_chars:
            out.append(buf);buf=sentence
        else:buf=candidate
    if buf:out.append(buf)
    return out

def independent_visible(url):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":"ProjectBrain-Independent-Generic-Evidence-Oracle/1.0",
            "Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(req,timeout=25) as response:
        raw=response.read(2_000_000)
        final=response.geturl()
        ctype=str(response.headers.get("Content-Type") or "")
    decoded=raw.decode("utf-8","replace")
    rows=[]
    if "html" in ctype.lower() or "<html" in decoded[:2000].lower():
        parser=Blocks();parser.feed(decoded)
        for value in parser.blocks:
            for unit in split_long(html.unescape(value)):
                unit=" ".join(unit.split())
                if len(unit)>=24:rows.append(unit)
    else:
        for value in re.split(r"\n\s*\n",decoded):
            for unit in split_long(html.unescape(value)):
                unit=" ".join(unit.split())
                if len(unit)>=24:rows.append(unit)
    dedup=[];seen=set()
    for x in rows:
        k=x.lower()
        if k in seen:continue
        seen.add(k);dedup.append(x)
    visible="\n".join(dedup)
    return final,visible

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

        final,visible=independent_visible(prov["final_url"])
        self.assertEqual(final,prov["final_url"])
        self.assertEqual(hashlib.sha256(visible.encode("utf-8")).hexdigest(),out["visible_text_sha256"])
        for unit in out["evidence_units"]:
            self.assertEqual(unit["text"],visible[unit["visible_text_start"]:unit["visible_text_end"]],unit)
            self.assertEqual(hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),unit["text_sha256"],unit)
            expected_id=hashlib.sha256(
                f'{out["page_raw_sha256"]}:{unit["visible_text_start"]}:{unit["visible_text_end"]}:{unit["text_sha256"]}'.encode("utf-8")
            ).hexdigest()
            self.assertEqual(expected_id,unit["evidence_unit_id"],unit)
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
