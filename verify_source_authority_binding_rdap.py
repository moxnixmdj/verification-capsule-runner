#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, re, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_rdap.py"
spec=importlib.util.spec_from_file_location("candidate_authority",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CASES=[
  ("python.org","Python Software Foundation"),
  ("pypi.org","Python Software Foundation"),
  ("w3.org","World Wide Web Consortium"),
  ("icann.org","Internet Corporation for Assigned Names and Numbers"),
  ("arxiv.org","Cornell University"),
  ("verisign.com","VeriSign"),
]

def raw_names(domain,timeout=20):
    req=urllib.request.Request("https://rdap.org/domain/"+urllib.parse.quote(domain,safe=""),
      headers={"User-Agent":"ProjectBrain-Independent-RDAP-Oracle/1","Accept":"application/rdap+json,application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=json.loads(r.read(2_000_000).decode("utf-8","replace"))
    out=[]
    def names(ent):
        vc=(ent or {}).get("vcardArray")
        if isinstance(vc,list) and len(vc)==2 and isinstance(vc[1],list):
            for item in vc[1]:
                if isinstance(item,list) and len(item)>=4 and str(item[0]).lower() in {"fn","org"}:
                    v=item[3]
                    if isinstance(v,list): v=" ".join(str(x) for x in v)
                    v=" ".join(str(v or "").split())
                    if v: out.append(v)
    for e in data.get("entities") or []:
        if "registrant" in {str(x).lower() for x in (e or {}).get("roles") or []}: names(e)
        for n in (e or {}).get("entities") or []:
            if "registrant" in {str(x).lower() for x in (n or {}).get("roles") or []}: names(n)
    return list(dict.fromkeys(out))

results=[]
passes=[]
for domain,entity in CASES:
    x=m.verify({"url":"https://"+domain+"/"},entity,timeout=20)
    row={"domain":domain,"claimed_entity":entity,"producer":x}
    if x.get("status")=="AUTHORITY_BINDING_VERIFIED":
        observed=raw_names(x.get("registered_domain") or domain)
        row["independent_registrant_names"]=observed
        row["independent_match"]=x.get("matched_registrant") in observed
        if row["independent_match"] and x.get("primary_source_status")=="UNVERIFIED" and x.get("relevance_status")=="UNVERIFIED":
            passes.append(domain)
    results.append(row)

# Live negative: a deliberately wrong entity must never verify, regardless of privacy.
negative=m.verify({"url":"https://python.org/"},"Completely Unrelated Example Corporation",timeout=20)
negative_ok=negative.get("status")=="UNVERIFIED"

# Safety boundary: local/private-ish inputs must fail before network.
private=m.verify({"url":"http://localhost/x"},"Anything",timeout=2)
private_ok=private.get("status")=="UNVERIFIED"

report={
  "schema":"PROJECT_BRAIN_SOURCE_AUTHORITY_BINDING_RDAP_QUALIFICATION_V1",
  "positive_required":2,
  "positive_passes":passes,
  "positive_pass_count":len(passes),
  "negative_mismatch_fail_closed":negative_ok,
  "private_host_fail_closed":private_ok,
  "results":results,
  "negative_result":negative,
  "private_result":private,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
}
report["qualified"]=len(passes)>=2 and negative_ok and private_ok
(ROOT/"source-authority-binding-rdap-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["qualified"] else 1)
