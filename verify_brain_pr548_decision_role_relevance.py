#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys

ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("pr548_ind_"+name,p)
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

# Cross-domain fixture A: thermophysical-like structure, different property/IDs.
objective=(
    "Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
    "is greater than that of annealed Alloy 408 under comparable bulk-material conditions."
)
wrong_property=(
    "Thermal ignition temperature of bulk annealed Alloy 7123 and Alloy 409 "
    "under comparable room-temperature conditions"
)
right_only="Thermal diffusivity measurements of annealed Alloy 408 near room temperature"
wrong_id="Thermal diffusivity measurements of annealed Alloy 409 near room temperature"

a=roles.evaluate(objective,wrong_property)
b=roles.evaluate(objective,right_only)
c=roles.evaluate(objective,wrong_id)
check("wrong_property_high_overlap_rejected",
      a.get("applicable") is True and a.get("verified") is False
      and (a.get("property_check") or {}).get("verified") is False,a)
check("correct_single_operand_source_admitted",
      b.get("applicable") is True and b.get("verified") is True
      and (b.get("operand_check") or {}).get("matched_discriminators")==["408"],b)
check("correct_property_wrong_operand_rejected",
      c.get("applicable") is True and c.get("verified") is False
      and (c.get("property_check") or {}).get("verified") is True
      and (c.get("operand_check") or {}).get("verified") is False,c)

# Cross-domain fixture B: battery property with alphanumeric model identities.
battery=(
    "Determine whether the specific heat capacity of Battery X900 is greater than "
    "that of Battery Y700."
)
check("battery_correct_role_admitted",
      roles.evaluate(battery,"Specific heat capacity measurements for Battery Y700").get("verified") is True)
check("battery_wrong_property_rejected",
      roles.evaluate(battery,"Specific power and heat generation measurements for Battery Y700").get("verified") is False)
check("battery_wrong_model_rejected",
      roles.evaluate(battery,"Specific heat capacity measurements for Battery Y701").get("verified") is False)

# Cross-domain fixture C: protocol identifiers, no 'that of' property shape.
protocol="Determine whether RFC 9110 is greater than RFC 7230."
pg=roles.evaluate(protocol,"RFC 9110 HTTP Semantics specification")
pb=roles.evaluate(protocol,"RFC 7540 HTTP/2 specification")
check("protocol_requested_identifier_admitted",pg.get("verified") is True,pg)
check("protocol_unrequested_identifier_rejected",pb.get("verified") is False,pb)

# Unsupported objective must not manufacture semantic authority.
broad="Find authoritative documentation about CSV parsing in Python."
bo=roles.evaluate(broad,"Python CSV parsing documentation")
check("unsupported_shape_preserves_legacy_path",
      bo.get("applicable") is False and bo.get("verified") is True,bo)

# End-to-end rank selection: raw lexical decoy is first, role-aware winner must replace it.
candidates=[
    {
      "url":"https://decoy.example/high",
      "title":"Thermal ignition temperature of bulk annealed Alloy 7123 and Alloy 409",
      "snippet":"room temperature comparable bulk material conditions alloy 7123 annealed",
    },
    {
      "url":"https://valid.example/right",
      "title":"Thermal diffusivity of annealed Alloy 408",
      "snippet":"measured thermal diffusivity near room temperature",
    },
]
ranked=ranker.rank(objective,candidates)
check("rank_status",ranked.get("status")=="LEXICAL_RELEVANCE_RANKED",ranked)
check("raw_decoy_really_ranked_first",ranked.get("raw_top_candidate_original_index")==0,ranked)
check("role_gate_selects_lower_correct_candidate",ranked.get("top_candidate_original_index")==1,ranked)
check("selected_receipt_verified",(ranked.get("top_candidate_admission") or {}).get("verified") is True,ranked)
rows={x.get("original_index"):x for x in ranked.get("ranked_candidates") or []}
check("decoy_receipt_rejected",
      ((rows.get(0) or {}).get("candidate_admission") or {}).get("verified") is False,rows.get(0))
check("correct_receipt_admitted",
      ((rows.get(1) or {}).get("candidate_admission") or {}).get("verified") is True,rows.get(1))

# Legacy non-comparison route remains the same BM25 receipt family.
legacy=ranker.rank(
    "find official python csv module documentation",
    [
      {"url":"https://docs.example/csv","title":"Python csv module","snippet":"CSV reading writing documentation"},
      {"url":"https://noise.example/garden","title":"Gardening","snippet":"soil plants"},
    ],
)
check("legacy_method_preserved",legacy.get("verification_method")=="DETERMINISTIC_BM25",legacy)
check("legacy_candidate_preserved",legacy.get("top_candidate_original_index")==0,legacy)
check("legacy_role_not_applicable",
      ((legacy.get("top_candidate_admission") or {}).get("decision_role") or {}).get("applicable") is False,
      legacy)

report={
  "schema":"BRAIN_PR548_DECISION_ROLE_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
  "status":"PASS" if not fail else "FAIL",
  "brain_pr":548,
  "brain_head_sha":"9ffe718550a08021ea14c73a22894737be6592cb",
  "failures":fail,
  "cases":cases,
  "parent_task_execution":False,
  "parent_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
}
(ROOT/"pr548-independent-report.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
