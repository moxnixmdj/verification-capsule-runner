#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, importlib.util, json, pathlib, re, urllib.parse, urllib.request
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

extractor=load("pr426_extract","canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py")
bm25=load("qualified_bm25","canonical/runtime/bound_capabilities/objective_relevance_bm25.py")
prov=load("qualified_provenance","canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py")

BLOCK={"h1","h2","h3","h4","h5","h6","p","li","dt","dd","blockquote","td","th","pre","main","article","section","div"}
SUPPRESS={"script","style","noscript","svg","nav","footer","header","form"}

def canon(x): return " ".join(str(x or "").split())
def sha(x):
    if isinstance(x,str): x=x.encode("utf-8")
    return hashlib.sha256(x).hexdigest()

class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.suppress=0; self.stack=[]; self.blocks=[]
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t in SUPPRESS: self.suppress+=1
        if self.suppress: return
        if t in BLOCK: self.stack.append([t,[]])
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
        _,parts=self.stack.pop(idx); text=canon(" ".join(parts))
        if text: self.blocks.append(text)
    def handle_data(self,data):
        if self.suppress or not self.stack: return
        text=canon(data)
        if text:
            for frame in self.stack: frame[1].append(text)

def split_long(text,max_chars=900):
    text=canon(text)
    if not text: return []
    if len(text)<=max_chars: return [text]
    s=[canon(p) for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",text) if canon(p)]
    if len(s)<=1: return [text[i:i+max_chars].strip() for i in range(0,len(text),max_chars) if text[i:i+max_chars].strip()]
    out=[]; buf=""
    for sentence in s:
        candidate=(buf+" "+sentence).strip() if buf else sentence
        if buf and len(candidate)>max_chars: out.append(buf); buf=sentence
        else: buf=candidate
    if buf: out.append(buf)
    return out

def independent_fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PR426-IndependentOracle/1.0","Accept":"text/html,application/xhtml+xml,text/plain,*/*;q=0.3"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(2_000_000); final=r.geturl(); ctype=str(r.headers.get("Content-Type") or "")
    return raw,final,ctype

def independent_visible(raw,ctype):
    decoded=raw.decode("utf-8","replace")
    if "html" in ctype.lower() or "<html" in decoded[:2000].lower():
        p=Blocks(); p.feed(decoded); rows=p.blocks
    else:
        rows=[x for x in re.split(r"\n\s*\n",decoded)]
    out=[]; seen=set()
    for value in rows:
        for unit in split_long(html.unescape(value)):
            unit=canon(unit)
            if len(unit)<24 or unit.lower() in seen: continue
            seen.add(unit.lower()); out.append(unit)
    return "\n".join(out)

def qualify(case):
    objective=case["objective"]; target=dict(case["candidate"])
    provenance=prov.verify(target,timeout=25)
    if provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        raise RuntimeError(case["id"]+":PROVENANCE_FAILED:"+json.dumps(provenance,sort_keys=True)[:800])
    distractor={"url":"https://example.com/unrelated","title":"gardening tomatoes irrigation greenhouse","snippet":"soil plants watering"}
    relevance=bm25.rank(objective,[target,distractor])
    if relevance.get("status")!="LEXICAL_RELEVANCE_RANKED" or relevance.get("top_candidate_original_index")!=0:
        raise RuntimeError(case["id"]+":BM25_SELECTION_FAILED:"+json.dumps(relevance,sort_keys=True)[:800])
    # No ROR/authority identity is passed here. This is the generic admission route.
    result=extractor.extract(objective,target,provenance,relevance,timeout=25,max_units=8)
    if result.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or not result.get("output_verified"):
        raise RuntimeError(case["id"]+":EXTRACTION_FAILED:"+json.dumps(result,sort_keys=True)[:1200])
    raw,final,ctype=independent_fetch(result["source_url"])
    visible=independent_visible(raw,ctype)
    if sha(raw)!=result.get("page_raw_sha256"): raise RuntimeError(case["id"]+":RAW_HASH_MISMATCH")
    if sha(visible)!=result.get("visible_text_sha256"): raise RuntimeError(case["id"]+":VISIBLE_HASH_MISMATCH")
    for unit in result.get("evidence_units") or []:
        text=unit["text"]
        start=int(unit["visible_text_start"]); end=int(unit["visible_text_end"])
        if visible[start:end]!=text: raise RuntimeError(case["id"]+":OFFSET_TEXT_MISMATCH")
        if sha(text)!=unit["text_sha256"]: raise RuntimeError(case["id"]+":TEXT_HASH_MISMATCH")
        if text not in visible: raise RuntimeError(case["id"]+":VERBATIM_MEMBERSHIP_MISMATCH")
        if len(unit.get("matched_objective_tokens") or [])<result.get("required_unit_match_count",1):
            raise RuntimeError(case["id"]+":OBJECTIVE_ANCHOR_MISMATCH")
    return {
      "id":case["id"],"pass":True,"source_url":result["source_url"],
      "unit_count":result["evidence_unit_count"],"ror_admission_used":False,
      "page_raw_sha256":result["page_raw_sha256"],
    }

cases=[
 {
  "id":"SQLITE_LOCKING_NON_ROR_ADMISSION",
  "objective":"SQLite database locking concurrency rollback journal transactions",
  "candidate":{
    "url":"https://www.sqlite.org/lockingv3.html",
    "title":"File Locking And Concurrency In SQLite Version 3",
    "snippet":"SQLite locking concurrency rollback journal database transactions"
  }
 },
 {
  "id":"RFC_HTTP_SEMANTICS_NON_ROR_ADMISSION",
  "objective":"HTTP semantics request response status methods protocol",
  "candidate":{
    "url":"https://www.rfc-editor.org/rfc/rfc9110.html",
    "title":"RFC 9110 HTTP Semantics",
    "snippet":"HTTP semantics request response status methods protocol"
  }
 }
]

report={"schema":"PROJECT_BRAIN_PR426_GENERIC_EXTRACTION_QUALIFICATION_V1","checks":[],"model_dependency_count":0,"incremental_spend_usd":0}
for case in cases: report["checks"].append(qualify(case))

# Fresh page relevance remains a separate fail-closed condition: discovery metadata
# can rank a candidate while the freshly retrieved body contains no usable units.
pypi_objective="SymPy Python symbolic mathematics library"
pypi_target={"url":"https://pypi.org/project/sympy/","title":"sympy · PyPI","snippet":"Python library for symbolic mathematics"}
pypi_prov=prov.verify(pypi_target,timeout=25)
pypi_rel=bm25.rank(pypi_objective,[pypi_target,{"url":"https://example.com/x","title":"gardening tomatoes","snippet":"soil irrigation"}])
pypi_result=extractor.extract(pypi_objective,pypi_target,pypi_prov,pypi_rel,timeout=25)
if pypi_result.get("reason")!="NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS":
    raise RuntimeError("FRESH_BODY_RELEVANCE_NEGATIVE_CONTROL_FAILED:"+json.dumps(pypi_result,sort_keys=True)[:800])
report["checks"].append({"id":"METADATA_RELEVANT_BUT_FRESH_BODY_UNGROUNDED_FAIL_CLOSED","pass":True})

# Fail closed: a receipt that selects a different candidate cannot admit the target.
objective=cases[0]["objective"]; target=cases[0]["candidate"]
p=prov.verify(target,timeout=25)
wrong=bm25.rank(objective,[{"url":"https://example.com/unrelated","title":objective,"snippet":objective},target])
bad=extractor.extract(objective,target,p,wrong,timeout=25)
if bad.get("reason")!="CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT":
    raise RuntimeError("WRONG_SELECTION_NEGATIVE_CONTROL_FAILED:"+json.dumps(bad,sort_keys=True)[:800])
report["checks"].append({"id":"WRONG_BM25_SELECTION_FAIL_CLOSED","pass":True})

report["all_pass"]=all(x.get("pass") for x in report["checks"])
out=ROOT/"pr426-generic-evidence-extraction-report.json"
out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if not report["all_pass"]: raise SystemExit(1)
