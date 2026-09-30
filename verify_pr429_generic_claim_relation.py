#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import urllib.request
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
PRODUCER_PATH=ROOT/"canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py"

spec=importlib.util.spec_from_file_location("pr429_producer",PRODUCER_PATH)
producer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)

def sha(value):
    if isinstance(value,str):
        value=value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def get_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PR429-IndependentVerifier/1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(6_000_000)
        return raw,r.geturl(),str(r.headers.get("Content-Type") or "")

def unit(page_sha,visible_sha,source_url,text,start):
    text=" ".join(str(text).split())
    end=start+len(text)
    text_sha=sha(text)
    uid=sha(f"{page_sha}:{start}:{end}:{text_sha}")
    return {
      "evidence_unit_id":uid,
      "source_url":source_url,
      "page_raw_sha256":page_sha,
      "visible_text_sha256":visible_sha,
      "text":text,
      "text_sha256":text_sha,
      "visible_text_start":start,
      "visible_text_end":end,
    }

def extraction(source_url,raw,texts):
    normalized=[" ".join(str(x).split()) for x in texts]
    visible="\n".join(normalized)
    page_sha=sha(raw)
    visible_sha=sha(visible)
    units=[]
    offset=0
    for text in normalized:
        units.append(unit(page_sha,visible_sha,source_url,text,offset))
        offset+=len(text)+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":source_url,
      "page_raw_sha256":page_sha,
      "visible_text_sha256":visible_sha,
      "evidence_units":units,
    }

report={
  "schema":"PROJECT_BRAIN_PR429_GENERIC_CLAIM_RELATION_QUALIFICATION_V1",
  "checks":[],
  "model_dependency_count":0,
  "incremental_spend_usd":0,
}

# Fresh economics numeric relation from World Bank live JSON.
wb_url="https://api.worldbank.org/v2/country/EGY/indicator/NY.GDP.MKTP.CD?format=json&per_page=100"
wb_raw,wb_final,_=get_bytes(wb_url)
wb=json.loads(wb_raw.decode("utf-8"))
rows=wb[1]
vals={str(x["date"]):x.get("value") for x in rows if x.get("value") is not None}
years=sorted(vals,reverse=True)[:2]
if len(years)<2:
    raise SystemExit("WORLD_BANK_VALUES_MISSING")
y0,y1=years
v0,v1=Decimal(str(vals[y0])),Decimal(str(vals[y1]))
econ=extraction(
    wb_final,wb_raw,
    [f"Egypt GDP observed value {v0} USD.",f"Egypt GDP prior value {v1} USD."]
)
u0,u1=[x["evidence_unit_id"] for x in econ["evidence_units"]]
out=producer.evaluate(econ,{
  "mode":"NUMERIC_RELATION","operator":"GT",
  "left":{"evidence_unit_id":u0,"numeric_literal_index":0},
  "right":{"evidence_unit_id":u1,"numeric_literal_index":0},
})
oracle=v0>v1
if out.get("status")!="NUMERIC_RELATION_VERIFIED" or out.get("predicate") is not oracle:
    raise SystemExit("WORLD_BANK_NUMERIC_ORACLE_MISMATCH")
if out.get("numeric_literal_semantic_role_status")!="UNVERIFIED":
    raise SystemExit("SEMANTIC_ROLE_OVERCLAIM")
report["checks"].append({"id":"WORLD_BANK_EGY_GDP_DECIMAL_RELATION","pass":True,"years":years,"oracle":oracle})

# Fresh software metadata exact-text support from PyPI.
pypi_url="https://pypi.org/pypi/sympy/1.14.0/json"
pypi_raw,pypi_final,_=get_bytes(pypi_url)
pypi=json.loads(pypi_raw.decode("utf-8"))
summary=" ".join(str(pypi["info"]["summary"]).split())
software=extraction(pypi_final,pypi_raw,[summary])
uid=software["evidence_units"][0]["evidence_unit_id"]
support=producer.evaluate(software,{
  "mode":"VERBATIM_SUPPORT","claim_text":summary,"evidence_unit_id":uid
})
if support.get("status")!="EXACT_TEXT_SUPPORT_VERIFIED" or not support.get("matches"):
    raise SystemExit("PYPI_VERBATIM_SUPPORT_MISMATCH")
negative=producer.evaluate(software,{
  "mode":"VERBATIM_SUPPORT","claim_text":summary+" definitely","evidence_unit_id":uid
})
if negative.get("status")!="EXACT_TEXT_SUPPORT_NOT_VERIFIED" or negative.get("matches"):
    raise SystemExit("PARAPHRASE_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"PYPI_SYMPY_EXACT_TEXT_SUPPORT","pass":True})

# Unit mismatch must fail closed.
bad=extraction(
    wb_final,wb_raw,
    [f"Left measurement {v0} USD.",f"Right measurement {v1} EUR."]
)
b0,b1=[x["evidence_unit_id"] for x in bad["evidence_units"]]
try:
    producer.evaluate(bad,{
      "mode":"NUMERIC_RELATION","operator":"GT",
      "left":{"evidence_unit_id":b0,"numeric_literal_index":0},
      "right":{"evidence_unit_id":b1,"numeric_literal_index":0},
    })
except ValueError as exc:
    if "UNIT_MISMATCH" not in str(exc):
        raise
else:
    raise SystemExit("UNIT_MISMATCH_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"UNIT_MISMATCH_FAIL_CLOSED","pass":True})

# Integrity tamper must fail closed.
tampered=json.loads(json.dumps(software))
tampered["evidence_units"][0]["text"]+=" altered"
try:
    producer.evaluate(tampered,{"mode":"VERBATIM_SUPPORT","claim_text":summary})
except ValueError as exc:
    if "TEXT_HASH_MISMATCH" not in str(exc):
        raise
else:
    raise SystemExit("TAMPER_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"EVIDENCE_HASH_TAMPER_FAIL_CLOSED","pass":True})

# Unsupported relation and bad reference must fail closed.
try:
    producer.evaluate(econ,{
      "mode":"NUMERIC_RELATION","operator":"APPROX",
      "left":{"evidence_unit_id":u0,"numeric_literal_index":0},
      "right":{"evidence_unit_id":u1,"numeric_literal_index":0},
    })
except ValueError as exc:
    if "OPERATOR_INVALID" not in str(exc):
        raise
else:
    raise SystemExit("UNSUPPORTED_OPERATOR_NEGATIVE_CONTROL_FAILED")

try:
    producer.evaluate(econ,{
      "mode":"NUMERIC_RELATION","operator":"EQ",
      "left":{"evidence_unit_id":"0"*64,"numeric_literal_index":0},
      "right":{"evidence_unit_id":u1,"numeric_literal_index":0},
    })
except ValueError as exc:
    if "REFERENCE_NOT_FOUND" not in str(exc):
        raise
else:
    raise SystemExit("BAD_REFERENCE_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"REFERENCE_AND_OPERATOR_FAIL_CLOSED","pass":True})

report["all_pass"]=all(x["pass"] for x in report["checks"])
report["producer_blob_expected"]="a68f8c08e5bc8f42178b21e1ff65ed0fa44c73b9"
report["test_blob_expected"]="590a1e50f11bc2903b56d41a00c5354ec2501c44"
path=ROOT/"pr429-generic-claim-relation-report.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if not report["all_pass"]:
    raise SystemExit(1)
