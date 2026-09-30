#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, re, urllib.request
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

bridge=load("bridge","canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py")
extractor=load("extractor","canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py")
bm25=load("bm25","canonical/runtime/bound_capabilities/objective_relevance_bm25.py")
prov=load("prov","canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py")

NUM=re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?"
)
def nums(text):
    out=[]
    for i,m in enumerate(NUM.finditer(text)):
        out.append((i,Decimal(m.group(1).replace(",",""))," ".join(str(m.group(2) or "").split()).lower()))
    return out

def live_extract(case):
    objective=case["objective"]; target=case["candidate"]
    p=prov.verify(target,timeout=25)
    if p.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        raise RuntimeError(case["id"]+":PROVENANCE_FAILED")
    distractor={"url":"https://example.com/unrelated","title":"gardening tomatoes irrigation","snippet":"soil plants greenhouse"}
    rel=bm25.rank(objective,[target,distractor])
    if rel.get("top_candidate_original_index")!=0:
        raise RuntimeError(case["id"]+":BM25_FAILED")
    ex=extractor.extract(objective,target,p,rel,timeout=25,max_units=12)
    if ex.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or not ex.get("output_verified"):
        raise RuntimeError(case["id"]+":EXTRACTION_FAILED:"+json.dumps(ex,sort_keys=True)[:1000])
    return ex

def verify_case(case):
    ex=live_extract(case)
    first=ex["evidence_units"][0]
    exact=bridge.evaluate(ex,{"mode":"VERBATIM_SUPPORT","claim_text":first["text"],"evidence_unit_id":first["evidence_unit_id"]})
    if exact.get("status")!="EXACT_TEXT_SUPPORT_VERIFIED" or len(exact.get("matches") or [])!=1:
        raise RuntimeError(case["id"]+":EXACT_SUPPORT_FAILED")
    bad=bridge.evaluate(ex,{"mode":"VERBATIM_SUPPORT","claim_text":first["text"]+" definitely","evidence_unit_id":first["evidence_unit_id"]})
    if bad.get("status")!="EXACT_TEXT_SUPPORT_NOT_VERIFIED":
        raise RuntimeError(case["id"]+":PARAPHRASE_NEGATIVE_FAILED")

    refs=[]
    for unit in ex["evidence_units"]:
        for idx,val,unit_text in nums(unit["text"]):
            refs.append((unit["evidence_unit_id"],idx,val,unit_text))
    pair=None
    for i,a in enumerate(refs):
        for b in refs[i+1:]:
            if a[3]==b[3]:
                pair=(a,b); break
        if pair: break
    if not pair:
        raise RuntimeError(case["id"]+":NO_NUMERIC_PAIR_FOR_LIVE_RELATION")
    a,b=pair
    spec={
      "mode":"NUMERIC_RELATION","operator":"GT",
      "left":{"evidence_unit_id":a[0],"numeric_literal_index":a[1]},
      "right":{"evidence_unit_id":b[0],"numeric_literal_index":b[1]},
    }
    got=bridge.evaluate(ex,spec)
    oracle=a[2]>b[2]
    if got.get("status")!="NUMERIC_RELATION_VERIFIED" or got.get("predicate") is not oracle:
        raise RuntimeError(case["id"]+":NUMERIC_ORACLE_MISMATCH")
    return {
      "id":case["id"],"pass":True,"source_url":ex["source_url"],
      "evidence_unit_count":ex["evidence_unit_count"],
      "exact_support_pass":True,"numeric_relation_pass":True,
      "numeric_oracle":oracle,"ror_admission_used":False,
    }

cases=[
 {"id":"SQLITE_GENERIC_V2_SUPPORT_RELATION","objective":"SQLite database locking concurrency rollback journal transactions",
  "candidate":{"url":"https://www.sqlite.org/lockingv3.html","title":"File Locking And Concurrency In SQLite Version 3","snippet":"SQLite locking concurrency rollback journal database transactions"}},
 {"id":"RFC_GENERIC_V2_SUPPORT_RELATION","objective":"HTTP semantics request response status methods protocol",
  "candidate":{"url":"https://www.rfc-editor.org/rfc/rfc9110.html","title":"RFC 9110 HTTP Semantics","snippet":"HTTP semantics request response status methods protocol"}}
]
report={"schema":"PROJECT_BRAIN_PR436_GENERIC_V2_CLAIM_RELATION_QUALIFICATION_V1","checks":[],"model_dependency_count":0,"incremental_spend_usd":0}
for case in cases: report["checks"].append(verify_case(case))

# Tamper control on real V2 output.
ex=live_extract(cases[0]); tampered=json.loads(json.dumps(ex)); tampered["evidence_units"][0]["text"]+=" altered"
try:
    bridge.evaluate(tampered,{"mode":"VERBATIM_SUPPORT","claim_text":"altered"})
except ValueError as e:
    if "TEXT_HASH_MISMATCH" not in str(e): raise
else:
    raise RuntimeError("TAMPER_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"REAL_V2_TAMPER_FAIL_CLOSED","pass":True})
report["all_pass"]=all(x.get("pass") for x in report["checks"])
out=ROOT/"pr436-generic-v2-claim-relation-report.json"
out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if not report["all_pass"]: raise SystemExit(1)
