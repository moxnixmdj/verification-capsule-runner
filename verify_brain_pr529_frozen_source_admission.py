#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr529_ind_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

front=load("open_research_source_frontend")
prov=load("source_candidate_provenance_verify")
ranker=load("objective_relevance_bm25")
extractor=load("objective_evidence_unit_extract")

fail=[]
cases=[]
def check(label,cond,detail=None):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)

# 1) Real relevance gate rejects weak subject coverage and admits strong coverage.
obj="Assess whether the RFC 9110 HTTP Semantics specification obsoletes RFC 7230 message syntax and routing."
weak=[{"url":"https://weak.example/x","title":"2026 technical overview","snippet":"RFC overview"}]
strong=[{"url":"https://strong.example/x","title":"RFC 9110 HTTP Semantics obsoletes RFC 7230 message syntax","snippet":"HTTP routing semantics"}]
rw=ranker.rank(obj,weak)
rs=ranker.rank(obj,strong)
check("weak_positive_bm25_not_admitted",
      rw.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and (rw.get("top_candidate_admission") or {}).get("verified") is False,rw)
check("strong_subject_coverage_admitted",
      rs.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and (rs.get("top_candidate_admission") or {}).get("verified") is True,rs)

# 2) Materializer requires a bound bibliographic receipt and candidate identity.
cand={"url":"https://doi.org/10.1000/example","doi":"10.1000/example","title":"Example"}
bad=prov.materialize(cand,{"status":"UNVERIFIED"},timeout=2,fetch=lambda *a: (_ for _ in ()).throw(AssertionError()))
check("materializer_requires_bibliographic_receipt",
      bad.get("reason")=="BIBLIOGRAPHIC_PROVENANCE_REQUIRED",bad)
mismatch=prov.materialize(cand,{
    "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
    "candidate_url":"https://doi.org/10.1000/different",
},timeout=2,fetch=lambda *a: (_ for _ in ()).throw(AssertionError()))
check("materializer_binds_candidate_identity",
      mismatch.get("reason")=="BIBLIOGRAPHIC_CANDIDATE_IDENTITY_MISMATCH",mismatch)

seen={}
def fake_fetch(url,timeout,accept):
    seen.update(url=url,timeout=timeout,accept=accept)
    return (b"<html><title>Publisher</title><body>technical evidence</body></html>",
            "text/html",200,"https://publisher.example/article")
ok=prov.materialize(cand,{
    "status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
    "candidate_url":cand["url"],
    "doi":"10.1000/example",
    "record_title":"Example",
    "verification_method":"CROSSREF_DOI_RECORD",
},timeout=3,fetch=fake_fetch)
check("materializer_preserves_bibliographic_chain",
      ok.get("status")=="RETRIEVAL_PROVENANCE_VERIFIED"
      and ok.get("bibliographic_provenance_status")=="VERIFIED"
      and ok.get("selected_only_materialization") is True
      and ok.get("authority_status")=="RETRIEVABILITY_VERIFIED__FACT_AUTHORITY_UNVERIFIED",ok)

# 3) Extractor independently enforces relevance admission.
candidate={"url":"https://example.org/source"}
provenance={"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"]}
row={"original_index":0,"candidate":candidate,"lexical_relevance_score":2.0,"matched_terms":["rfc","http"]}
rel_base={
    "status":"LEXICAL_RELEVANCE_RANKED","verification_method":"DETERMINISTIC_BM25",
    "output_verified":True,"objective":"RFC HTTP","top_candidate_original_index":0,
    "ranked_candidates":[row],
}
_,reason=extractor._qualified_relevance_source("RFC HTTP",candidate,provenance,{**rel_base,
    "top_candidate_admission":{"verified":False,"matched_term_count":2}})
check("extractor_rejects_unadmitted_relevance",
      reason=="RELEVANCE_SUBJECT_COVERAGE_ADMISSION_REQUIRED",reason)
url,reason=extractor._qualified_relevance_source("RFC HTTP",candidate,provenance,{**rel_base,
    "top_candidate_admission":{"verified":True,"matched_term_count":2}})
check("extractor_accepts_admitted_matching_receipt",
      url=="https://example.org/source" and reason is None,{"url":url,"reason":reason})

# 4) Frontend path: bibliographic winner is preserved; failed direct materialization gets exactly one metadata-anchored retry.
objective="Assess whether the lithium battery thermal runaway study measured a threshold response."
def decomp():
    return {"status":"DECOMPOSED","objective":objective,"question_shape":"BOOLEAN_ASSESSMENT","roles":[{"role":"SOURCE_DISCOVERY"}]}

class Discovery:
    def __init__(self,refined=True):
        self.calls=[]; self.refined=refined
    def discover(self,obj,limit=12,timeout=15,query_override=None):
        self.calls.append(query_override)
        if query_override is not None:
            return {"status":"CANDIDATES_DISCOVERED" if self.refined else "DISCOVERY_UNAVAILABLE",
                    "objective":obj,"query":query_override,
                    "candidates":([{"url":"https://refined.example/live","title":"Lithium battery thermal runaway threshold response","snippet":"measured response"}] if self.refined else [])}
        return {"status":"CANDIDATES_DISCOVERED","objective":obj,"candidates":[
            {"url":"https://weak.example/page","title":"2026 overview","snippet":"general overview"},
            {"url":"https://doi.org/10.1000/battery","doi":"10.1000/battery","title":"Lithium battery thermal runaway threshold response study","snippet":"measured response"},
        ]}
class Verifier:
    def __init__(self): self.materialize_calls=[]
    def verify(self,c,timeout=15):
        if c.get("doi"):
            return {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","candidate_url":c["url"],"doi":c["doi"],
                    "record_title":"Lithium battery thermal runaway threshold response study","publisher":"Example"}
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":c["url"],"final_url":c["url"],
                "final_host":c["url"].split("/")[2]}
    def materialize(self,c,bibliographic_verification,timeout=15,fetch=None):
        self.materialize_calls.append(c["url"])
        return {"status":"UNVERIFIED","reason":"BIBLIOGRAPHIC_SELECTED_LIVE_MATERIALIZATION_FAILED"}
class Relevance:
    def rank(self,obj,candidates):
        idx=1 if len(candidates)>1 else 0
        chosen=candidates[idx]
        return {"status":"LEXICAL_RELEVANCE_RANKED","verification_method":"DETERMINISTIC_BM25",
                "output_verified":True,"objective":obj,"query_focus":{"query":"lithium battery thermal runaway threshold response"},
                "top_candidate_original_index":idx,
                "top_candidate_admission":{"verified":True,"matched_term_count":4},
                "ranked_candidates":[{"original_index":i,"candidate":c,"lexical_relevance_score":5.0 if i==idx else 1.0,
                                      "matched_terms":["lithium","battery","threshold","response"] if i==idx else ["2026"]}
                                     for i,c in enumerate(candidates)]}
class Extractor:
    def __init__(self): self.calls=[]
    def extract(self,obj,c,p,r,timeout=15):
        self.calls.append((c,p))
        return {"status":"EVIDENCE_EXTRACTION_BLOCKED","reason":"QUALIFIER_STOPS_AFTER_ROUTING"}
class Binder:
    def bind(self,*a,**k): raise AssertionError("BINDER_MUST_NOT_RUN")
class Authority:
    def bind_candidate(self,c,timeout=15): return {"status":"UNVERIFIED","reason":"QUALIFIER_FIXTURE"}

def run_front(refined):
    d=Discovery(refined); v=Verifier(); x=Extractor()
    original=front._load_sibling
    mapping={"open_web_source_candidate_discovery":d,"source_candidate_provenance_verify":v,
             "objective_relevance_bm25":Relevance(),"objective_evidence_unit_extract":x,
             "objective_claim_operand_binding":Binder(),"source_authority_binding_ror":Authority()}
    front._load_sibling=lambda n:mapping[n]
    try: out=front.run(objective,decomp(),limit=8,timeout=2)
    finally: front._load_sibling=original
    return out,d,v,x

out,d,v,x=run_front(True)
check("frontend_one_metadata_refined_retry",
      out.get("status")=="SOURCE_FRONTEND_READY"
      and v.materialize_calls==["https://doi.org/10.1000/battery"]
      and len(d.calls)==2 and d.calls[0] is None
      and "Lithium battery thermal runaway threshold response study" in str(d.calls[1])
      and out.get("selected_source_origin")=="BIBLIOGRAPHIC_METADATA_REFINED_LIVE_RETRIEVAL"
      and len(x.calls)==1,
      {"out":out,"calls":d.calls,"materialize":v.materialize_calls,"extract_calls":len(x.calls)})
out2,d2,v2,x2=run_front(False)
check("frontend_failed_refinement_fails_closed",
      out2.get("status")=="SELECTED_SOURCE_MATERIALIZATION_BLOCKED"
      and len(d2.calls)==2 and len(x2.calls)==0,out2)

report={"schema":"BRAIN_PR529_FROZEN_SOURCE_ADMISSION_INDEPENDENT_QUALIFICATION_V1",
        "status":"PASS" if not fail else "FAIL",
        "brain_pr":529,
        "brain_head_sha":"4df38e5aa55cfd86a1fda6fbe11666ab6221da2c",
        "failures":fail,"cases":cases,
        "parent_task_execution":False,"parent_task_replay":False,
        "model_dependency_count":0,"incremental_spend_usd":0}
(ROOT/"pr529-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
