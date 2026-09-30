#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, importlib.util, pathlib, re, sys, unittest, urllib.request
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"
EXPECTED={
  "objective_evidence_unit_extract.py":"6598ba92307c55fe6e645b4ecba070d2259818e2",
  "open_research_source_frontend.py":"46fe82d74a35d9318a134fb95e1d5cecfc2dd485",
  "objective_relevance_bm25.py":"95d2b6bac6f6ffb5db97526407fcd22cbcc6c790",
  "source_candidate_provenance_verify.py":"1dc26e68d18010b66211d1d83f7b2024c8ad1fcf",
}
BLOCK={"h1","h2","h3","h4","h5","h6","p","li","dt","dd","blockquote","td","th","pre"}
SUPPRESS={"script","style","noscript","svg","nav","footer","header","form"}

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("qual_"+name,p)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

def canon(x): return " ".join(str(x or "").split())

class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress=0; self.stack=[]; self.blocks=[]
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t in SUPPRESS: self.suppress+=1
        if not self.suppress and t in BLOCK: self.stack.append([t,[]])
    def handle_endtag(self,tag):
        t=tag.lower()
        if t in SUPPRESS:
            if self.suppress: self.suppress-=1
            return
        if self.suppress or t not in BLOCK or not self.stack: return
        idx=None
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==t: idx=i; break
        if idx is None: return
        name,parts=self.stack.pop(idx)
        value=canon(" ".join(parts))
        if value: self.blocks.append((name,value))
    def handle_data(self,data):
        if self.suppress or not self.stack: return
        v=canon(data)
        if v:
            for frame in self.stack: frame[1].append(v)

def split_long(text,max_chars=900):
    text=canon(text)
    if not text: return []
    if len(text)<=max_chars: return [text]
    ss=[canon(x) for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text) if canon(x)]
    if len(ss)<=1:
        return [text[i:i+max_chars].strip() for i in range(0,len(text),max_chars) if text[i:i+max_chars].strip()]
    out=[]; buf=""
    for s in ss:
        c=(buf+" "+s).strip() if buf else s
        if buf and len(c)>max_chars: out.append(buf); buf=s
        else: buf=c
    if buf: out.append(buf)
    return out

def visible_blocks(raw,ctype):
    decoded=raw.decode("utf-8","replace")
    if "html" in ctype.lower() or "<html" in decoded[:2000].lower():
        p=Blocks(); p.feed(decoded); rows=p.blocks
    else:
        rows=[("text",x) for x in re.split(r"\n\s*\n",decoded)]
    out=[]; seen=set()
    for tag,value in rows:
        for unit in split_long(html.unescape(value)):
            unit=canon(unit)
            if len(unit)<24: continue
            key=unit.lower()
            if key in seen: continue
            seen.add(key); out.append((tag,unit))
    return out

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-GenericExtraction/1.0","Accept":"text/html,text/plain,*/*;q=0.3"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return r.read(2_000_000),r.geturl(),str(r.headers.get("Content-Type") or ""),int(getattr(r,"status",200))

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor=load("objective_evidence_unit_extract")
        cls.relevance=load("objective_relevance_bm25")
        cls.provenance=load("source_candidate_provenance_verify")

    def test_exact_blobs(self):
        for name,expected in EXPECTED.items():
            self.assertEqual(git_blob(BOUND/name),expected,name)

    def _case(self,objective,candidate,distractor):
        prov=self.provenance.verify(candidate,timeout=25)
        self.assertEqual(prov.get("status"),"RETRIEVAL_PROVENANCE_VERIFIED",prov)
        # Rebind the candidate URL to the verified final URL when the source uses
        # a canonical redirect. The extractor still requires exact same-source identity.
        final=prov["final_url"]
        live_candidate=dict(candidate); live_candidate["url"]=final
        prov=dict(prov); prov["candidate_url"]=final; prov["final_url"]=final
        candidates=[live_candidate,distractor]
        rel=self.relevance.rank(objective,candidates)
        self.assertEqual(rel.get("status"),"LEXICAL_RELEVANCE_RANKED",rel)
        self.assertEqual(rel.get("top_candidate_original_index"),0,rel)
        out=self.extractor.extract(objective,live_candidate,prov,rel,timeout=25,max_units=10)
        self.assertEqual(out.get("status"),"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",out)
        self.assertGreater(out.get("evidence_unit_count",0),0,out)
        self.assertEqual(out.get("model_dependency_count"),0)
        self.assertEqual(out.get("incremental_spend_usd"),0)
        self.assertEqual(out.get("claim_relation_status"),"UNVERIFIED")
        self.assertEqual(out.get("factual_correctness_status"),"UNVERIFIED")
        self.assertNotIn("authority_identity",out)

        raw,url,ctype,status=fetch(final)
        self.assertEqual(url,final)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),out["page_raw_sha256"])
        blocks=visible_blocks(raw,ctype)
        visible="\n".join(text for _,text in blocks)
        self.assertEqual(hashlib.sha256(visible.encode()).hexdigest(),out["visible_text_sha256"])
        for unit in out["evidence_units"]:
            text=unit["text"]
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),unit["text_sha256"])
            start,end=unit["visible_text_start"],unit["visible_text_end"]
            self.assertEqual(visible[start:end],text)
            expected_id=hashlib.sha256(
                f'{out["page_raw_sha256"]}:{start}:{end}:{unit["text_sha256"]}'.encode()
            ).hexdigest()
            self.assertEqual(unit["evidence_unit_id"],expected_id)
            self.assertEqual(unit["source_url"],final)
            self.assertGreaterEqual(len(unit["matched_objective_tokens"]),1)
        return out

    def test_fresh_rfc_http_semantics(self):
        self._case(
          "Assess HTTP conditional requests cache validation semantics and validators",
          {"url":"https://www.rfc-editor.org/rfc/rfc9110.html","title":"RFC 9110 HTTP Semantics conditional requests validators","snippet":"HTTP semantics validators conditional requests cache validation"},
          {"url":"https://example.com/gardening","title":"Garden watering schedule","snippet":"plants soil sunlight"},
        )

    def test_fresh_sqlite_wal(self):
        self._case(
          "Assess SQLite write ahead logging WAL checkpoint behavior database transactions",
          {"url":"https://www.sqlite.org/wal.html","title":"SQLite Write-Ahead Logging WAL","snippet":"WAL checkpoint database transaction behavior"},
          {"url":"https://example.com/weather","title":"Weather forecast","snippet":"rain wind temperature"},
        )

    def test_candidate_mismatch_fails_before_fetch(self):
        objective="Assess SQLite WAL checkpoint behavior"
        candidate={"url":"https://example.org/a"}
        prov={"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":"https://example.org/a","final_url":"https://example.org/a"}
        rel={
          "objective":objective,"status":"LEXICAL_RELEVANCE_RANKED",
          "verification_method":"DETERMINISTIC_BM25","output_verified":True,
          "top_candidate_original_index":0,
          "ranked_candidates":[{"original_index":0,"candidate":{"url":"https://example.org/b"},"lexical_relevance_score":1.0,"matched_terms":["sqlite"]}],
        }
        out=self.extractor.extract(objective,candidate,prov,rel,fetch=lambda *a: (_ for _ in ()).throw(AssertionError("must not fetch")))
        self.assertEqual(out.get("reason"),"CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
