#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, re, sys
from rank_bm25 import BM25Okapi

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
spec=importlib.util.spec_from_file_location("candidate_bm25",P)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)

CASES=[
  {
    "objective":"Assess whether lithium ion battery calendar aging increases at elevated temperature",
    "candidates":[
      {"title":"Lithium-ion battery calendar aging at elevated temperature","snippet":"capacity fade storage temperature state of charge calendar aging"},
      {"title":"Battery recycling policy update","snippet":"collection recycling legislation"},
      {"title":"Marine corrosion handbook","snippet":"salt water steel corrosion"},
    ],
    "expected":0,
  },
  {
    "objective":"Determine how HTTP ETag validation affects stale cache response reuse",
    "candidates":[
      {"title":"DNS resolver configuration","snippet":"nameserver cache dns records"},
      {"title":"HTTP caching validation with ETag","snippet":"stale response validator conditional request ETag cache reuse"},
      {"title":"TLS certificate deployment","snippet":"certificate handshake encryption"},
    ],
    "expected":1,
  },
  {
    "objective":"Compare volcanic sulfur dioxide emissions with satellite observations",
    "candidates":[
      {"title":"Satellite observations of volcanic sulfur dioxide","snippet":"SO2 plume volcano emissions remote sensing satellite"},
      {"title":"Earthquake early warning","snippet":"seismic waves alerts"},
      {"title":"Atmospheric methane inventory","snippet":"methane sources greenhouse gas"},
    ],
    "expected":0,
  },
]

def independent_tokens(text):
    generic={"a","an","and","are","as","at","be","by","for","from","how","in","is","it","of","on","or","that","the","this","to","was","were","what","when","where","which","who","why","with","whether","determine","find","compare","using"}
    return [x for x in re.findall(r"[a-z0-9]+",str(text).lower()) if len(x)>1 and x not in generic]

rows=[]; ok=True
for case in CASES:
    out=m.rank(case["objective"],case["candidates"])
    corpus=[]
    for c in case["candidates"]:
        text=" ".join([c.get("title",""),c.get("title",""),c.get("record_title",""),c.get("snippet","")])
        corpus.append(independent_tokens(text))
    oracle=BM25Okapi(corpus)
    scores=oracle.get_scores(independent_tokens(case["objective"]))
    oracle_top=max(range(len(scores)),key=lambda i:(scores[i],-i))
    passed=(out.get("status")=="LEXICAL_RELEVANCE_RANKED"
            and out.get("top_candidate_original_index")==case["expected"]
            and oracle_top==case["expected"]
            and out.get("semantic_entailment_status")=="UNVERIFIED"
            and out.get("primary_source_status")=="UNVERIFIED"
            and out.get("model_dependency_count")==0)
    rows.append({"objective":case["objective"],"producer_top":out.get("top_candidate_original_index"),"oracle_top":oracle_top,"expected":case["expected"],"pass":passed})
    ok=ok and passed

no_overlap=m.rank("quantum entanglement Bell photon",[
 {"title":"banana recipe","snippet":"flour sugar"},
 {"title":"football scores","snippet":"league table"},
])
no_overlap_ok=no_overlap.get("status")=="RELEVANCE_UNRESOLVED" and not no_overlap.get("output_verified",False)
tie=m.rank("alpha",[{"title":"alpha beta"},{"title":"alpha beta"}])
tie_ok=[x["original_index"] for x in tie.get("ranked_candidates",[])]==[0,1]

report={
 "schema":"PROJECT_BRAIN_PR410_OBJECTIVE_RELEVANCE_BM25_QUALIFICATION_V1",
 "fresh_cross_domain_cases":rows,
 "no_overlap_fail_closed":no_overlap_ok,
 "deterministic_tie":tie_ok,
 "qualified":ok and no_overlap_ok and tie_ok,
 "model_dependency_count":0,
 "incremental_spend_usd":0,
}
(ROOT/"pr410-objective-relevance-bm25-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["qualified"] else 1)
