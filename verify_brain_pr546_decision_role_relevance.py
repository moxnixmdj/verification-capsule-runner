#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
spec=importlib.util.spec_from_file_location("independent_decision_role_relevance",P)
if spec is None or spec.loader is None:
    raise RuntimeError("LOAD_FAILED")
ranker=importlib.util.module_from_spec(spec); sys.modules[spec.name]=ranker; spec.loader.exec_module(ranker)
fail=[]; cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)

materials=(
  "Determine whether the room-temperature thermal conductivity of annealed "
  "6061 aluminum is greater than that of annealed 304 stainless steel "
  "under comparable bulk-material conditions."
)
decoy={
 "title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
 "record_title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
 "snippet":"6061 aluminum 302 stainless steel bulk temperature oxygen ignition"
}
correct={
 "title":"Thermal conductivity and electrical resistivity of a sample of AISI type 304 stainless steel",
 "record_title":"Thermal conductivity and electrical resistivity of a sample of AISI type 304 stainless steel",
 "snippet":"National Bureau of Standards thermal conductivity 304 stainless steel"
}
m=ranker.rank(materials,[decoy,correct])
check("task_c_correct_record_selected",
      m.get("status")=="LEXICAL_RELEVANCE_RANKED" and m.get("top_candidate_original_index")==1,m)
rows={x["original_index"]:x for x in m.get("ranked_candidates",[])}
check("task_c_decoy_role_rejected",
      0 in rows and (rows[0].get("decision_role_admission") or {}).get("verified") is False,
      rows.get(0))
check("task_c_correct_role_admitted",
      1 in rows and (rows[1].get("decision_role_admission") or {}).get("verified") is True,
      rows.get(1))
check("task_c_zero_model_dependency",m.get("model_dependency_count")==0,m)

# Cross-domain: high lexical overlap on the wrong property must not beat an
# operand+property anchored source.
pop=ranker.rank(
 "Determine whether France population growth is higher than Germany population growth.",
 [
   {"title":"France GDP growth and Germany GDP growth","snippet":"France Germany growth outlook"},
   {"title":"France population growth","snippet":"France population growth demographic estimate"},
   {"title":"Germany population growth","snippet":"Germany population growth demographic estimate"}
 ])
check("population_property_preserved",
      pop.get("status")=="LEXICAL_RELEVANCE_RANKED" and pop.get("top_candidate_original_index") in {1,2},pop)
prow={x["original_index"]:x for x in pop.get("ranked_candidates",[])}
check("population_gdp_decoy_rejected",
      0 in prow and (prow[0].get("decision_role_admission") or {}).get("verified") is False,
      prow.get(0))

# Exact discriminators are semantic identity anchors, not optional BM25 terms.
alloy=ranker.rank(
 "Determine whether the thermal conductivity of alloy 6061 aluminum is greater than that of alloy 304 stainless steel.",
 [{"title":"Thermal conductivity of alloy 302 stainless steel","snippet":"thermal conductivity stainless steel alloy 302"}]
)
check("wrong_numeric_operand_fails_closed",
      alloy.get("status")=="RELEVANCE_UNRESOLVED"
      and alloy.get("reason")=="NO_DECISION_ROLE_ADMISSIBLE_CANDIDATE",alloy)

# Uppercase one-character discriminators are preserved through the reused parser.
labels=ranker.rank(
 "Determine whether the orbital period of Planet Kepler A is greater than that of Planet Kepler B.",
 [
   {"title":"Orbital period of Planet Kepler B","snippet":"Planet Kepler B orbital period measurement"},
   {"title":"Orbital period of Planet Kepler C","snippet":"Planet Kepler C orbital period measurement"}
 ])
check("single_character_role_identity",
      labels.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and labels.get("top_candidate_original_index")==0,labels)

# If an explicit comparison cannot yield a property role, do not silently fall
# back to aggregate token-count admission.
amb=ranker.rank(
 "Determine whether France is greater than Germany.",
 [{"title":"France Germany comparison","snippet":"France Germany"}]
)
check("unresolved_explicit_roles_fail_closed",
      amb.get("status")=="RELEVANCE_UNRESOLVED"
      and amb.get("reason")=="DECISION_ROLE_SPEC_UNRESOLVED",amb)

# Non-relation research keeps the already-qualified lexical path.
plain=ranker.rank(
 "find official python csv module documentation",
 [
   {"title":"Python csv module","snippet":"CSV file reading writing documentation"},
   {"title":"Python weather","snippet":"forecast"}
 ])
check("non_relation_backward_compatible",
      plain.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and plain.get("top_candidate_original_index")==0
      and plain.get("verification_method")=="DETERMINISTIC_BM25",plain)

source=P.read_text(encoding="utf-8").lower()
check("no_model_supplier_in_candidate",
      all(x not in source for x in ("pollinations","openai","anthropic","model_api")),{})

report={
 "schema":"BRAIN_PR546_DECISION_ROLE_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS" if not fail else "FAIL",
 "brain_pr":546,
 "brain_candidate_head":"d6431d5522c295a6ce54468280d3941182ea05aa",
 "failures":fail,
 "cases":cases,
 "parent_task_execution":False,
 "parent_task_replay":False,
 "spent_materials_task_c_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr546-independent-decision-role-report.json").write_text(
 json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
