#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent

def load(rel,name):
    p=ROOT/rel
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise RuntimeError("LOAD_FAILED:"+rel)
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

roles=load("canonical/runtime/bound_capabilities/decision_role_relevance_admission.py","pr549_roles")
rank=load("canonical/runtime/bound_capabilities/objective_relevance_bm25.py","pr549_rank")
cases=[]
def check(name,cond,detail):
    if not cond: raise AssertionError(name+":"+repr(detail))
    cases.append({"case":name,"status":"PASS"})

objective=("Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
           "is greater than that of annealed Alloy 408 under comparable bulk-material conditions.")
wrong_property="Room-temperature ignition behavior of annealed Alloy 7123 under comparable bulk-material conditions"
x=roles.evaluate(objective,wrong_property)
check("FRESH_WRONG_PROPERTY_REJECTED",x["applicable"] and not x["verified"],x)
check("FRESH_PROPERTY_CORE_IS_THERMAL_DIFFUSIVITY",
      x["property_check"]["requested_property_tokens"]==["thermal","diffusivity"],x)

wrong_operand="Thermal diffusivity measurements of annealed Alloy 409 near room temperature"
x=roles.evaluate(objective,wrong_operand)
check("FRESH_WRONG_OPERAND_REJECTED",
      x["applicable"] and x["property_check"]["verified"] and not x["operand_check"]["verified"] and not x["verified"],x)

one_operand="Thermal diffusivity measurements of annealed Alloy 408 near room temperature"
x=roles.evaluate(objective,one_operand)
check("FRESH_ONE_REQUESTED_OPERAND_SOURCE_ADMITTED",x["verified"],x)
check("FRESH_EXACT_NUMERIC_OPERAND_BOUND",x["operand_check"].get("matched_discriminators")==["408"],x)

ranked=rank.rank(objective,[
 {"title":"Ignition temperature of annealed Alloy 7123","snippet":"room temperature thermal behavior comparable bulk material conditions"},
 {"title":"Thermal diffusivity of annealed Alloy 408","snippet":"measured thermal diffusivity near room temperature"},
])
check("FRESH_RANKER_BYPASSES_HIGHER_WRONG_ROLE",
      ranked["raw_top_candidate_original_index"]==0
      and ranked["top_candidate_original_index"]==1
      and ranked["top_candidate_admission"]["verified"] is True,ranked)

protocol="Determine whether RFC 9110 is greater than RFC 7230."
good=roles.evaluate(protocol,"RFC 9110 HTTP Semantics")
bad=roles.evaluate(protocol,"RFC 7540 HTTP/2 overview")
check("FRESH_PROTOCOL_REQUESTED_ID_ADMITTED",good["applicable"] and good["verified"],good)
check("FRESH_PROTOCOL_UNREQUESTED_ID_REJECTED",bad["applicable"] and not bad["verified"],bad)

threshold="Determine whether observed wave amplitude exceeds 1 meter."
r=roles.evaluate(threshold,"Observed wave amplitude measurements from monitoring record")
check("NUMERIC_THRESHOLD_ROLE_GATE_NOT_APPLICABLE",
      r["applicable"] is False and r["verified"] is True
      and r.get("reason")=="NUMERIC_THRESHOLD_COMPARISON_PRESERVES_INCUMBENT_RELEVANCE",r)
rr=rank.rank(threshold,[
 {"title":"Observed wave amplitude measurements","snippet":"maximum wave amplitude monitoring record"},
 {"title":"Weather bulletin","snippet":"temperature and wind"},
])
check("NUMERIC_THRESHOLD_INCUMBENT_RANKING_PRESERVED",
      rr["top_candidate_original_index"]==0
      and rr["top_candidate_admission"]["verified"] is True
      and rr["top_candidate_admission"]["decision_role"]["applicable"] is False,rr)

broad="Find authoritative documentation about thermal management for electronic enclosures."
br=rank.rank(broad,[
 {"title":"Thermal management for electronic enclosures","snippet":"authoritative technical documentation"},
 {"title":"Gardening notes","snippet":"soil and plants"},
])
check("BROAD_NONCOMPARISON_LEGACY_PRESERVED",
      br["top_candidate_original_index"]==0
      and br["top_candidate_admission"]["verified"] is True
      and br["top_candidate_admission"]["decision_role"]["applicable"] is False,br)

report={
 "schema":"PROJECT_BRAIN_PR549_THRESHOLD_SAFE_DECISION_ROLE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS","brain_pr":549,
 "brain_candidate_head":"85a572980596f50c18ea6645b0a72b3681185c14",
 "cases":cases,
 "parent_task_execution":False,"parent_task_replay":False,
 "materials_task_c_replay":False,"model_dependency_count":0,"incremental_spend_usd":0
}
(ROOT/"pr549-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
