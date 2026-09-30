#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, urllib.parse, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_ror.py"
s=importlib.util.spec_from_file_location("ror_candidate",P)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

POS=["harvard.edu","nasa.gov"]
NEG=["docs.harvard.edu","example.org"]

def independent(domain):
    url="https://api.ror.org/v2/organizations?"+urllib.parse.urlencode({"query.advanced":f'domains:"{domain}"'})
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-ROR-Independent-Oracle/1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r:
        data=json.loads(r.read(3_000_000).decode("utf-8","replace"))
    exact=[]
    for record in data.get("items") or []:
        if str(record.get("status") or "").lower()!="active": continue
        domains=[]
        for raw in record.get("domains") or []:
            h=m._safe_host(raw)
            if h and h not in domains: domains.append(h)
        if domain in domains:
            exact.append({"id":record.get("id"),"domains":domains})
    return exact

rows=[]; positives=[]
for domain in POS:
    out=m.bind_candidate({"url":"https://"+domain+"/"},timeout=20)
    oracle=independent(domain)
    ok=(out.get("status")=="AUTHORITY_IDENTITY_VERIFIED"
        and len(oracle)==1
        and out.get("ror_id")==oracle[0].get("id")
        and out.get("matched_domain")==domain
        and out.get("primary_source_status")=="UNVERIFIED"
        and out.get("relevance_status")=="UNVERIFIED"
        and out.get("evidence_sufficiency_status")=="UNVERIFIED")
    rows.append({"domain":domain,"producer":out,"oracle":oracle,"pass":ok})
    if ok: positives.append(domain)

negrows=[]; negok=True
for domain in NEG:
    out=m.bind_candidate({"url":"https://"+domain+"/"},timeout=20)
    oracle=independent(domain)
    ok=(out.get("status")!="AUTHORITY_IDENTITY_VERIFIED" and not oracle)
    negrows.append({"domain":domain,"producer":out,"oracle":oracle,"pass":ok})
    negok=negok and ok

report={
 "schema":"PROJECT_BRAIN_SOURCE_AUTHORITY_BINDING_ROR_QUALIFICATION_V1",
 "positive_passes":positives,
 "positive_required":2,
 "negative_cases":negrows,
 "positive_cases":rows,
 "qualified":len(positives)==2 and negok,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"source-authority-binding-ror-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["qualified"] else 1)
