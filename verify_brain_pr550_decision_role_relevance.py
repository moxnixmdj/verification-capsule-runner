#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
BOUND=ROOT/"canonical/runtime/bound_capabilities"
def load(name):
    p=BOUND/(name+".py")
    s=importlib.util.spec_from_file_location("pr550_ind_"+name,p)
    if s is None or s.loader is None: raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m
rank=load("objective_relevance_bm25")
roles=load("decision_role_relevance_admission")
fail=[]; cases=[]
def check(label,cond,detail):
    cases.append({"label":label,"pass":bool(cond),"detail":detail})
    if not cond: fail.append(label)

# Reconstruct the causal Task-C shape without replaying the task.
obj=("Determine whether the room-temperature thermal conductivity of annealed "
     "6061 aluminum is greater than that of annealed 304 stainless steel "
     "under comparable bulk-material conditions.")
wrong={"title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
       "snippet":"room temperature bulk 6061 aluminum 302 stainless steel oxygen ignition temperature"}
right={"title":"Thermal conductivity and electrical resistivity of a sample of AISI type 304 stainless steel",
       "snippet":"National Bureau of Standards thermal conductivity 304 stainless steel"}
out=rank.rank(obj,[wrong,right])
check("task_c_decoy_not_selected",
      out.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and out.get("top_candidate_original_index")==1,out)
rows={r["original_index"]:r for r in out.get("ranked_candidates",[])}
check("task_c_wrong_property_or_operand_rejected",
      0 in rows and (rows[0].get("candidate_admission") or {}).get("verified") is False,
      rows.get(0))
check("task_c_correct_operand_source_admitted",
      1 in rows and (rows[1].get("candidate_admission") or {}).get("verified") is True,
      rows.get(1))

# Cross-domain property/operand evidence.
cross=rank.rank(
 "Determine whether France population growth is higher than Germany population growth.",
 [
  {"title":"France GDP growth and Germany GDP growth","snippet":"France Germany economic growth"},
  {"title":"France population growth","snippet":"France population growth demographic estimate"},
  {"title":"Germany population growth","snippet":"Germany population growth demographic estimate"}
 ])
check("cross_domain_wrong_property_rejected",
      cross.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and cross.get("top_candidate_original_index") in {1,2},cross)

# Hard numeric entity discriminator must distinguish requested operand.
alloy=roles.evaluate(
 "Determine whether the thermal diffusivity of Alloy 7123 is greater than that of Alloy 408.",
 "Thermal diffusivity of Alloy 409"
)
check("wrong_hard_operand_id_rejected",
      alloy.get("applicable") is True and alloy.get("verified") is False,alloy)

# Numeric threshold is deliberately outside entity-vs-entity role gating.
threshold_obj="Determine whether observed wave amplitude exceeds 1 meter."
threshold_role=roles.evaluate(threshold_obj,"Observed wave amplitude measurements from the monitoring record")
threshold_rank=rank.rank(threshold_obj,[
 {"title":"Observed wave amplitude measurements","snippet":"maximum wave amplitude monitoring record"},
 {"title":"Weather bulletin","snippet":"temperature and wind"}
])
check("numeric_threshold_preserves_incumbent",
      threshold_role.get("applicable") is False
      and threshold_role.get("verified") is True
      and threshold_role.get("reason")=="NUMERIC_THRESHOLD_COMPARISON_PRESERVES_INCUMBENT_RELEVANCE"
      and threshold_rank.get("top_candidate_original_index")==0,
      {"role":threshold_role,"rank":threshold_rank})

# Unsupported broad/noncomparison shape must keep legacy relevance semantics.
broad=rank.rank(
 "Find authoritative documentation about thermal management for electronic enclosures.",
 [
  {"title":"Thermal management for electronic enclosures","snippet":"authoritative technical documentation"},
  {"title":"Gardening notes","snippet":"soil plants"}
 ])
check("broad_noncomparison_backward_compatible",
      broad.get("status")=="LEXICAL_RELEVANCE_RANKED"
      and broad.get("top_candidate_original_index")==0
      and (broad.get("top_candidate_admission") or {}).get("decision_role",{}).get("applicable") is False,
      broad)

# Distinct protocol-number case: role identity, not generic subject overlap.
proto=roles.evaluate("Determine whether RFC 9110 is greater than RFC 7230.","RFC 9110 HTTP Semantics")
proto_bad=roles.evaluate("Determine whether RFC 9110 is greater than RFC 7230.","RFC 7540 HTTP/2 overview")
check("protocol_discriminators",
      proto.get("verified") is True and proto_bad.get("verified") is False,
      {"good":proto,"bad":proto_bad})

source=(BOUND/"decision_role_relevance_admission.py").read_text(encoding="utf-8").lower()
rank_source=(BOUND/"objective_relevance_bm25.py").read_text(encoding="utf-8").lower()
check("zero_model_supplier_strings",
      all(x not in source+rank_source for x in ("pollinations","openai","anthropic","model_api")),{})

report={
 "schema":"BRAIN_PR550_THRESHOLD_SAFE_DECISION_ROLE_RELEVANCE_INDEPENDENT_QUALIFICATION_V1",
 "status":"PASS" if not fail else "FAIL",
 "brain_pr":550,
 "brain_candidate_head":"3b8ab760e12c1cac8949240ebf8e15ec94937121",
 "failures":fail,
 "cases":cases,
 "parent_task_execution":False,
 "parent_task_replay":False,
 "spent_materials_task_c_replay":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
(ROOT/"pr550-independent-decision-role-report.json").write_text(
 json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if not fail else 1)
