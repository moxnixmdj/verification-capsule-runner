#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("oracle_"+name,p)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m
def sha(x):
    if isinstance(x,str): x=x.encode()
    return hashlib.sha256(x).hexdigest()
def extraction(texts):
    page=sha(b"independent-integration-oracle")
    visible="\n".join(texts); vsha=sha(visible); rows=[]; off=0
    for text in texts:
        tsha=sha(text); start=off; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({"evidence_unit_id":uid,"source_url":"https://oracle.example/evidence",
          "page_raw_sha256":page,"visible_text_sha256":vsha,"text":text,"text_sha256":tsha,
          "visible_text_start":start,"visible_text_end":end})
        off=end+1
    return {"schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED","output_verified":True,
      "source_url":"https://oracle.example/evidence","page_raw_sha256":page,
      "visible_text_sha256":vsha,"evidence_unit_count":len(rows),"evidence_units":rows}

front=load("open_research_source_frontend")
real=front._load_sibling
class D:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","candidates":[{"url":"https://oracle.example/evidence","title":"Evidence","snippet":objective}]}
class P:
    @staticmethod
    def verify(candidate,timeout=15):
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","candidate_url":candidate["url"],"final_url":candidate["url"],"final_host":"oracle.example"}
class R:
    @staticmethod
    def rank(objective,candidates):
        return {"status":"LEXICAL_RELEVANCE_RANKED","verification_method":"DETERMINISTIC_BM25","output_verified":True,
          "objective":objective,"top_candidate_original_index":0,
          "ranked_candidates":[{"original_index":0,"lexical_relevance_score":3.0,"matched_terms":["protocol"],"candidate":candidates[0]}]}
class A:
    @staticmethod
    def bind_candidate(candidate,timeout=15): return {"status":"UNVERIFIED","reason":"OPTIONAL"}
binder=real("objective_claim_operand_binding")
current_texts=[]
class E:
    @staticmethod
    def extract(objective,candidate,provenance,relevance,timeout=15): return extraction(current_texts)
mods={"open_web_source_candidate_discovery":D,"source_candidate_provenance_verify":P,
      "objective_relevance_bm25":R,"objective_evidence_unit_extract":E,
      "source_authority_binding_ror":A,"objective_claim_operand_binding":binder}
front._load_sibling=lambda name: mods[name]

def dec(obj):
    return {"status":"DECOMPOSED","objective":obj,"question_shape":"COMPARATIVE",
      "roles":[{"role":"SOURCE_DISCOVERY"},{"role":"EVIDENCE_ACQUISITION"},{"role":"EVIDENCE_EXTRACTION"},
               {"role":"RELATION_EVALUATION"},{"role":"DECISION_SYNTHESIS_AND_VERIFICATION"}]}

try:
    current_texts[:]=["Protocol Alpha window was 65535 bytes.","Protocol Beta window was 32768 bytes."]
    obj="Determine whether Protocol Alpha window is greater than Protocol Beta window."
    out=front.run(obj,dec(obj),limit=2,timeout=2)
    assert out["claim_relation_evaluated_count"]==1, out
    b=out["claim_relation_evaluations"][0]["binding"]
    assert b["status"]=="CLAIM_SPEC_AND_OPERANDS_BOUND", b
    assert b["relation_result"]["status"]=="NUMERIC_RELATION_VERIFIED", b
    assert b["relation_result"]["predicate"] is True, b
    assert out["next_required_capability"]=="MODEL_INDEPENDENT_DECISION_QUALITY_SYNTHESIS_AND_VERIFICATION_FROM_OBJECTIVE_BOUND_RELATION_V1", out
    assert out["factual_correctness_claims_made"] is False and out["evidence_sufficiency_claims_made"] is False

    current_texts[:]=["The protocol retry interval is 5 seconds.","Reference revision was 2026."]
    obj='Verify whether the evidence states "The protocol retry interval is 5 seconds."'
    out=front.run(obj,dec(obj),limit=2,timeout=2)
    assert out["claim_relation_evaluated_count"]==1, out
    b=out["claim_relation_evaluations"][0]["binding"]
    assert b["relation_result"]["status"]=="EXACT_TEXT_SUPPORT_VERIFIED", b

    current_texts[:]=["Protocol Alpha window was 65535 bytes.","Protocol Beta window was 32768 bytes."]
    obj="Compare Protocol Alpha and Protocol Beta window."
    out=front.run(obj,dec(obj),limit=2,timeout=2)
    assert out["claim_relation_evaluated_count"]==0, out
    assert out["next_required_capability"]=="MODEL_INDEPENDENT_CLAIM_SPEC_AND_OPERAND_BINDING_FROM_OBJECTIVE_AND_GENERIC_EVIDENCE_V1", out

    rt=(ROOT/"canonical/runtime/astra_runtime.py").read_text()
    assert "OPEN_ENDED_RESEARCH_RELATION_EVALUATED__" in rt
    assert "DECISION_SYNTHESIS_AND_VERIFICATION_REQUIRED" in rt
    print("INDEPENDENT_OPEN_RESEARCH_CLAIM_PIPELINE_INTEGRATION_PASS")
finally:
    front._load_sibling=real
