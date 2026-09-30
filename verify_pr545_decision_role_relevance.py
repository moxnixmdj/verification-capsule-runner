#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
spec=importlib.util.spec_from_file_location("pr545_candidate",P)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)

cases=[]

materials=(
 "Determine whether the room-temperature thermal conductivity of annealed Alloy 6061 "
 "is greater than that of annealed Steel 304."
)
material_candidates=[
 {
   "title":"Room-temperature ignition behavior of annealed Alloy 6061 and Steel 302",
   "snippet":"thermal measurements annealed alloy 6061 stainless steel 302 ignition temperature",
 },
 {
   "title":"Room-temperature thermal conductivity of annealed Alloy 6061 and Steel 304",
   "snippet":"thermal conductivity measurements for annealed alloy 6061 and stainless steel 304",
 },
]
m=mod.rank(materials,material_candidates)
assert m["status"]=="LEXICAL_RELEVANCE_RANKED",m
rows={x["original_index"]:x for x in m["ranked_candidates"]}
assert rows[0]["lexical_relevance_score"]>0,rows[0]
assert rows[0]["decision_role_admission"]["verified"] is False,rows[0]
assert rows[1]["decision_role_admission"]["verified"] is True,rows[1]
assert m["top_candidate_original_index"]==1,m
assert m["top_candidate_admission"]["verified"] is True,m
cases.append({"case":"MATERIALS_WRONG_PROPERTY_AND_OPERAND_REJECTED","status":"PASS"})

demo="Determine whether France population growth is greater than Germany population growth."
d=mod.rank(demo,[
 {"title":"France and Spain population growth","snippet":"annual population growth France Spain demographic rates"},
 {"title":"France and Germany population growth","snippet":"annual population growth France Germany demographic rates"},
])
rows={x["original_index"]:x for x in d["ranked_candidates"]}
assert rows[0]["decision_role_admission"]["verified"] is False,rows[0]
assert rows[1]["decision_role_admission"]["verified"] is True,rows[1]
assert d["top_candidate_original_index"]==1,d
cases.append({"case":"DEMOGRAPHY_DISTINCT_OPERANDS_REQUIRED","status":"PASS"})

astro="Determine whether Mars orbital period is greater than Venus orbital period."
a=mod.rank(astro,[
 {"title":"Mars and Mercury orbital period comparison","snippet":"planet orbital period Mars Mercury"},
 {"title":"Mars and Venus orbital period comparison","snippet":"planet orbital period Mars Venus"},
])
rows={x["original_index"]:x for x in a["ranked_candidates"]}
assert rows[0]["decision_role_admission"]["verified"] is False,rows[0]
assert rows[1]["decision_role_admission"]["verified"] is True,rows[1]
assert a["top_candidate_original_index"]==1,a
cases.append({"case":"ASTRONOMY_DISTINCT_OPERANDS_REQUIRED","status":"PASS"})

legacy=mod.rank("find official python csv module documentation",[
 {"title":"Python csv module","snippet":"CSV file reading writing documentation"},
 {"title":"Weather forecast","snippet":"rain"},
])
assert legacy["decision_role_spec"] is None,legacy
assert legacy["top_candidate_original_index"]==0,legacy
assert legacy["top_candidate_admission"]["verified"] is True,legacy
assert legacy["top_candidate_admission"]["decision_role_coverage"]["applicable"] is False,legacy
cases.append({"case":"NONCOMPARISON_LEGACY_ADMISSION_PRESERVED","status":"PASS"})

report={
 "schema":"PROJECT_BRAIN_PR545_DECISION_ROLE_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":545,
 "candidate_blob":"62c39a7076f0e5ab8c916d4ff93ce02f8c90149d",
 "parser_blob":"48fd058430d8d361fc75beced567c7b6d1166531",
 "focus_blob":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
 "cases":cases,
 "parent_task_execution":False,
 "materials_task_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr545-independent-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
