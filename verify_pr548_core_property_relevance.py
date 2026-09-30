#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("pr548_oracle_"+name,p)
    if s is None or s.loader is None: raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

roles=load("decision_role_relevance_admission")
ranker=load("objective_relevance_bm25")
cases=[]

objective=(
 "Determine whether the room-temperature electrical resistivity of annealed Alloy 8457 "
 "is greater than that of annealed Alloy 216 under comparable bulk-material conditions."
)
wrong_property="Electrical ignition temperature of annealed Alloy 8457 and Alloy 217 near room temperature"
x=roles.evaluate(objective,wrong_property)
assert x["applicable"] is True,x
assert x["verified"] is False,x
assert x["property_check"]["verified"] is False,x
cases.append({"case":"WRONG_PROPERTY_REJECTED","status":"PASS"})

wrong_operand="Room-temperature electrical resistivity measurements for annealed Alloy 217"
x=roles.evaluate(objective,wrong_operand)
assert x["property_check"]["verified"] is True,x
assert x["operand_check"]["verified"] is False,x
assert x["verified"] is False,x
cases.append({"case":"WRONG_OPERAND_ID_REJECTED","status":"PASS"})

right_operand="Room-temperature electrical resistivity measurements for annealed Alloy 216"
x=roles.evaluate(objective,right_operand)
assert x["property_check"]["verified"] is True,x
assert x["operand_check"]["verified"] is True,x
assert x["verified"] is True,x
cases.append({"case":"PROPERTY_PLUS_REQUESTED_OPERAND_ADMITTED","status":"PASS"})

ranked=ranker.rank(objective,[
 {
  "title":"Electrical ignition temperature of annealed Alloy 8457 and Alloy 217",
  "snippet":"room temperature bulk material conditions annealed alloy electrical measurements",
 },
 {
  "title":"Electrical resistivity of annealed Alloy 216",
  "snippet":"room-temperature bulk electrical resistivity measurements",
 },
])
assert ranked["status"]=="LEXICAL_RELEVANCE_RANKED",ranked
assert ranked["raw_top_candidate_original_index"]==0,ranked
assert ranked["top_candidate_original_index"]==1,ranked
assert ranked["ranked_candidates"][0]["candidate_admission"]["decision_role"]["verified"] is False,ranked
assert ranked["top_candidate_admission"]["verified"] is True,ranked
cases.append({"case":"RANKER_SKIPS_HIGHER_SCORING_WRONG_ROLE","status":"PASS"})

protocol="Determine whether RFC 9308 is greater than RFC 7540."
good=roles.evaluate(protocol,"RFC 9308 protocol technical specification")
bad=roles.evaluate(protocol,"RFC 9110 HTTP semantics")
assert good["applicable"] and good["verified"],good
assert bad["applicable"] and not bad["verified"],bad
cases.append({"case":"PROTOCOL_OPERAND_DISCRIMINATOR","status":"PASS"})

legacy=ranker.rank("Find authoritative documentation about photovoltaic module degradation",[
 {"title":"Photovoltaic module degradation documentation","snippet":"authoritative technical report"},
 {"title":"Cooking recipes","snippet":"kitchen"},
])
assert legacy["top_candidate_original_index"]==0,legacy
role=legacy["top_candidate_admission"]["decision_role"]
assert role["applicable"] is False and role["verified"] is True,legacy
cases.append({"case":"UNSUPPORTED_SHAPE_PRESERVES_LEGACY","status":"PASS"})

report={
 "schema":"PROJECT_BRAIN_PR548_CORE_PROPERTY_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":548,
 "candidate_blobs":{
  "decision_role_relevance_admission":"4a0d49386c3c1410a09d847fddd9772545ba0095",
  "objective_relevance_bm25":"0abb5225fe9fba2443f2df46b2e41bd1c7dd7436",
  "objective_claim_operand_binding":"48fd058430d8d361fc75beced567c7b6d1166531",
  "research_query_focus":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"
 },
 "cases":cases,
 "parent_task_execution":False,
 "materials_task_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr548-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
