#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, re, sys
from rank_bm25 import BM25Okapi
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
s=importlib.util.spec_from_file_location("candidate_bm25",P)
m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)

CASES=[
 ("Assess whether lithium ion battery calendar aging increases at elevated temperature",[
   {"title":"Lithium-ion battery calendar aging at elevated temperature","snippet":"capacity fade storage temperature state of charge calendar aging"},
   {"title":"Battery recycling policy update","snippet":"collection recycling legislation"},
   {"title":"Marine corrosion handbook","snippet":"salt water steel corrosion"}],0),
 ("Determine how HTTP ETag validation affects stale cache response reuse",[
   {"title":"DNS resolver configuration","snippet":"nameserver cache dns records"},
   {"title":"HTTP caching validation with ETag","snippet":"stale response validator conditional request ETag cache reuse"},
   {"title":"TLS certificate deployment","snippet":"certificate handshake encryption"}],1),
 ("Compare volcanic sulfur dioxide emissions with satellite observations",[
   {"title":"Satellite observations of volcanic sulfur dioxide","snippet":"SO2 plume volcano emissions remote sensing satellite"},
   {"title":"Earthquake early warning","snippet":"seismic waves alerts"},
   {"title":"Atmospheric methane inventory","snippet":"methane sources greenhouse gas"}],0),
]
GENERIC={"a","an","and","are","as","at","be","by","for","from","how","in","is","it","of","on","or","that","the","this","to","was","were","what","when","where","which","who","why","with","whether","determine","find","compare","using"}
def tok(x):
    return [z for z in re.findall(r"[a-z0-9]+",str(x).lower()) if len(z)>1 and z not in GENERIC]
rows=[]; good=True
for objective,candidates,expected in CASES:
    out=m.rank(objective,candidates)
    corpus=[tok(" ".join([c.get("title",""),c.get("title",""),c.get("record_title",""),c.get("snippet","")])) for c in candidates]
    scores=BM25Okapi(corpus).get_scores(tok(objective))
    oracle=max(range(len(scores)),key=lambda i:(scores[i],-i))
    passed=(out.get("status")=="LEXICAL_RELEVANCE_RANKED" and out.get("top_candidate_original_index")==expected
            and oracle==expected and out.get("semantic_entailment_status")=="UNVERIFIED"
            and out.get("primary_source_status")=="UNVERIFIED" and out.get("model_dependency_count")==0)
    rows.append({"objective":objective,"producer_top":out.get("top_candidate_original_index"),"oracle_top":oracle,"expected":expected,"pass":passed})
    good=good and passed
no=m.rank("quantum entanglement Bell photon",[{"title":"banana recipe","snippet":"flour sugar"},{"title":"football scores","snippet":"league table"}])
no_ok=no.get("status")=="RELEVANCE_UNRESOLVED" and not no.get("output_verified",False)
tie=m.rank("alpha",[{"title":"alpha beta"},{"title":"alpha beta"}])
tie_ok=[x["original_index"] for x in tie.get("ranked_candidates",[])]==[0,1]
report={"schema":"PROJECT_BRAIN_PR410_OBJECTIVE_RELEVANCE_BM25_QUALIFICATION_V1","cases":rows,"no_overlap_fail_closed":no_ok,"deterministic_tie":tie_ok,"qualified":good and no_ok and tie_ok,"model_dependency_count":0,"incremental_spend_usd":0}
(ROOT/"pr410-objective-relevance-bm25-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report["qualified"] else 1)
