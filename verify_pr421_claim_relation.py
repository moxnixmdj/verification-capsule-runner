#!/usr/bin/env python3
import importlib.util, json, pathlib, urllib.request
from decimal import Decimal

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_claim_relation.py"
spec=importlib.util.spec_from_file_location("producer",P)
producer=importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PR421-IndependentVerifier/1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read(5_000_000).decode("utf-8"))

report={"schema":"PROJECT_BRAIN_PR421_CROSS_DOMAIN_QUALIFICATION_V1","checks":[],"model_dependency_count":0,"incremental_spend_usd":0}

# Fresh economics numeric relation.
wb=get_json("https://api.worldbank.org/v2/country/EGY/indicator/NY.GDP.MKTP.CD?format=json&per_page=100")
rows=wb[1]
vals={str(x["date"]):x.get("value") for x in rows if x.get("value") is not None}
years=sorted(vals,reverse=True)[:2]
if len(years)<2: raise SystemExit("WORLD_BANK_VALUES_MISSING")
y0,y1=years[0],years[1]
v0,v1=Decimal(str(vals[y0])),Decimal(str(vals[y1]))
econ={
 "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
 "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED","output_verified":True,
 "fresh_url":"https://api.worldbank.org/",
 "evidence_records":[
  {"ordinal":0,"text":f"Egypt GDP {y0} was {v0} USD.","text_sha256":"a"*64,"numeric_literals":[f"{v0} USD"],"source_url":"https://api.worldbank.org/"},
  {"ordinal":1,"text":f"Egypt GDP {y1} was {v1} USD.","text_sha256":"b"*64,"numeric_literals":[f"{v1} USD"],"source_url":"https://api.worldbank.org/"}
 ]
}
prod=producer.evaluate(econ,{"mode":"NUMERIC_RELATION","operator":"GT","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0}})
oracle=(v0>v1)
if prod.get("predicate") is not oracle or prod.get("status")!="RELATION_VERIFIED": raise SystemExit("ECON_NUMERIC_ORACLE_MISMATCH")
report["checks"].append({"id":"WORLD_BANK_EGY_GDP_GT","pass":True,"years":[y0,y1],"oracle":oracle})

# Fresh software-package verbatim support.
pypi=get_json("https://pypi.org/pypi/sympy/1.14.0/json")
summary=" ".join(str(pypi["info"]["summary"]).split())
software={
 "schema":"PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1",
 "status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED","output_verified":True,
 "fresh_url":"https://pypi.org/project/sympy/",
 "evidence_records":[{"ordinal":7,"text":summary,"text_sha256":"c"*64,"numeric_literals":[],"source_url":"https://pypi.org/project/sympy/"}]
}
prod2=producer.evaluate(software,{"mode":"VERBATIM_TEXT","claim_text":summary})
if prod2.get("status")!="SUPPORT_VERIFIED" or not prod2.get("matches"): raise SystemExit("PYPI_VERBATIM_ORACLE_MISMATCH")
prod3=producer.evaluate(software,{"mode":"VERBATIM_TEXT","claim_text":summary+" definitely"})
if prod3.get("status")!="SUPPORT_NOT_VERIFIED": raise SystemExit("PARAPHRASE_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"PYPI_SYMPY_VERBATIM","pass":True})

# Independent fail-closed unit mismatch.
bad=json.loads(json.dumps(econ)); bad["evidence_records"][1]["numeric_literals"]=[f"{v1} EUR"]
try:
    producer.evaluate(bad,{"mode":"NUMERIC_RELATION","operator":"GT","left":{"record_ordinal":0,"numeric_literal_index":0},"right":{"record_ordinal":1,"numeric_literal_index":0}})
except ValueError as e:
    if "UNIT_MISMATCH" not in str(e): raise
else:
    raise SystemExit("UNIT_MISMATCH_NEGATIVE_CONTROL_FAILED")
report["checks"].append({"id":"UNIT_MISMATCH_FAIL_CLOSED","pass":True})

report["all_pass"]=all(x["pass"] for x in report["checks"])
path=ROOT/"pr421-claim-relation-report.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if not report["all_pass"]: raise SystemExit(1)
