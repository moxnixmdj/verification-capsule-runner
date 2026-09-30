#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/decision_role_relevance_admission.py"
R=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"

def load(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
roles=load(P,"pr548_roles")
rank=load(R,"pr548_rank")
cases=[]

def ok(name,cond,detail=None):
    if not cond: raise AssertionError(f"{name}: {detail}")
    cases.append({"case":name,"status":"PASS"})

objective=("Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
           "is greater than that of annealed Alloy 408 under comparable bulk-material conditions.")
wrong_property="Room-temperature ignition behavior of annealed Alloy 7123 under comparable bulk conditions"
a=roles.evaluate(objective,wrong_property)
ok("WRONG_PROPERTY_REJECTED",a["applicable"] and not a["verified"],a)
ok("CORE_PROPERTY_EXACT",a["property_check"]["requested_property_tokens"]==["thermal","diffusivity"],a)

wrong_operand="Thermal diffusivity of annealed Alloy 409 near room temperature"
b=roles.evaluate(objective,wrong_operand)
ok("WRONG_OPERAND_REJECTED",b["applicable"] and not b["verified"],b)

one_operand="Thermal diffusivity measurements of annealed Alloy 408 near room temperature"
c=roles.evaluate(objective,one_operand)
ok("RELEVANT_ONE_OPERAND_ADMITTED",c["verified"],c)
ok("RIGHT_IDENTIFIER_MATCHED",c["operand_check"].get("matched_discriminators")==["408"],c)

ranked=rank.rank(objective,[
  {"title":"Ignition temperature of annealed Alloy 7123","snippet":"room temperature thermal behavior bulk conditions"},
  {"title":"Thermal diffusivity of annealed Alloy 408","snippet":"room temperature measured thermal diffusivity"},
])
ok("RANKER_SKIPS_HIGH_OVERLAP_WRONG_PROPERTY",
   ranked["top_candidate_original_index"]==1 and ranked["top_candidate_admission"]["verified"],ranked)

protocol="Determine whether RFC 9110 is greater than RFC 7230."
good=roles.evaluate(protocol,"RFC 9110 HTTP Semantics")
bad=roles.evaluate(protocol,"RFC 7540 HTTP/2 overview")
ok("PROTOCOL_OPERAND_GOOD",good["verified"],good)
ok("PROTOCOL_OPERAND_WRONG_REJECTED",not bad["verified"],bad)

legacy=rank.rank("find official python csv module documentation",[
 {"title":"Python csv module","snippet":"CSV reading writing documentation"},
 {"title":"Weather forecast","snippet":"rain"},
])
ok("NONCOMPARISON_LEGACY_PRESERVED",
   legacy["top_candidate_original_index"]==0 and legacy["top_candidate_admission"]["verified"],legacy)

report={
 "schema":"PROJECT_BRAIN_PR548_DECISION_ROLE_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS","brain_pr":548,
 "brain_candidate_head":"9ffe718550a08021ea14c73a22894737be6592cb",
 "cases":cases,"parent_task_execution":False,"materials_task_replay":False,
 "model_dependency_count":0,"incremental_spend_usd":0
}
(ROOT/"pr548-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,sort_keys=True))
