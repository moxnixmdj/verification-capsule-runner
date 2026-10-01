#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr549_ind_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

roles=load("decision_role_relevance_admission")
ranker=load("objective_relevance_bm25")

fail=[]
cases=[]
def check(label,cond,detail=None):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond:
        fail.append(label)

objective=(
    "Determine whether the optical band gap of annealed ceramic Q17 "
    "is greater than that of annealed ceramic R42 under comparable conditions."
)
candidates=[
    {
        "url":"https://decoy.example/high-overlap",
        "title":"Melting temperature of bulk annealed ceramic Q17 and ceramic R41",
        "snippet":"optical comparison under comparable annealed ceramic conditions",
    },
    {
        "url":"https://wrong-id.example/property",
        "title":"Optical band gap of annealed ceramic R41",
        "snippet":"band gap measurement under comparable conditions",
    },
    {
        "url":"https://right.example/property",
        "title":"Optical band gap of annealed ceramic R42",
        "snippet":"reference optical band gap measurement",
    },
]
out=ranker.rank(objective,candidates)
check("cross_domain_ranked",out.get("status")=="LEXICAL_RELEVANCE_RANKED",out)
check("cross_domain_correct_role_selected",out.get("top_candidate_original_index")==2,out)
rows={x.get("original_index"):x for x in out.get("ranked_candidates") or []}
check("wrong_property_rejected",
      not ((rows.get(0) or {}).get("candidate_admission") or {}).get("decision_role",{}).get("verified",False),
      rows.get(0))
check("wrong_discriminator_rejected",
      not ((rows.get(1) or {}).get("candidate_admission") or {}).get("decision_role",{}).get("verified",False),
      rows.get(1))
check("correct_property_operand_admitted",
      ((rows.get(2) or {}).get("candidate_admission") or {}).get("decision_role",{}).get("verified") is True,
      rows.get(2))

protocol="Determine whether RFC 9110 is greater than RFC 7230."
good=roles.evaluate(protocol,"RFC 9110 HTTP Semantics")
bad=roles.evaluate(protocol,"RFC 7540 HTTP/2 overview")
check("protocol_good_operand",good.get("applicable") is True and good.get("verified") is True,good)
check("protocol_wrong_operand",bad.get("applicable") is True and bad.get("verified") is False,bad)

threshold="Determine whether observed rainfall depth exceeds 50 mm."
role=roles.evaluate(threshold,"Observed rainfall depth monitoring record")
check("threshold_gate_not_applicable",
      role.get("applicable") is False and role.get("verified") is True
      and role.get("reason")=="NUMERIC_THRESHOLD_COMPARISON_PRESERVES_INCUMBENT_RELEVANCE",
      role)
threshold_rank=ranker.rank(threshold,[
    {"title":"Observed rainfall depth monitoring record","snippet":"rainfall depth observations"},
    {"title":"Wind speed bulletin","snippet":"wind forecast"},
])
check("threshold_incumbent_ranking_preserved",
      threshold_rank.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and threshold_rank.get("top_candidate_original_index")==0
      and ((threshold_rank.get("top_candidate_admission") or {}).get("decision_role") or {}).get("applicable") is False,
      threshold_rank)

broad="Explain thermal management approaches for power electronics."
broad_role=roles.evaluate(broad,"Thermal management approaches for power electronics")
check("unsupported_shape_preserves_incumbent",
      broad_role.get("applicable") is False and broad_role.get("verified") is True,broad_role)

report={
    "schema":"BRAIN_PR549_THRESHOLD_SAFE_DECISION_ROLE_INDEPENDENT_QUALIFICATION_V1",
    "status":"PASS" if not fail else "FAIL",
    "brain_pr":549,
    "brain_head_sha":"85a572980596f50c18ea6645b0a72b3681185c14",
    "failures":fail,
    "cases":cases,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "materials_task_c_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
}
(ROOT/"pr549-independent-report.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
