#!/usr/bin/env python3
from __future__ import annotations
import copy, json, pathlib, sys

R=pathlib.Path(__file__).resolve().parent
SCHEMA="PROJECT_BRAIN_ROOT3_MINIMUM_ACTION_CUT_INDEPENDENT_VERIFIER_V1"

def load(name):
    x=json.loads((R/"fixtures"/name).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(name)
    return x

def derive(activation,coalescence,superportfolio,saturation,residual,composition):
    errors=[]
    if activation.get("current_truth",{}).get("live_root3_predicates")!=11:
        errors.append("ROOT3_COUNT")
    if "11_ROOT3_TARGETS_TO_4_WORK_CLASSES" not in str(activation.get("status","")):
        errors.append("ACTIVATION")
    acc=coalescence.get("accounting") or {}
    if acc.get("formal_root3_target_count")!=7 or acc.get("population_group_count")!=4:
        errors.append("POPULATION_COMPRESSION")
    cur=saturation.get("current_matched_surface_result") or {}
    if cur.get("pair_count")!=96 or cur.get("direct_reuse_closures")!=0:
        errors.append("SATURATION")
    oth=saturation.get("other_live_root3_target_result") or {}
    if oth.get("current_full_protocol_transmutation_witness_count")!=0:
        errors.append("NEW_FULL_PROTOCOL_WITNESS")
    if oth.get("current_normalized_direct_reuse_closure_count")!=0:
        errors.append("NEW_DIRECT_REUSE")
    ex=superportfolio.get("execution_compression") or {}
    if ex.get("matched_scope_target_count")!=8 or ex.get("shared_future_superportfolio_wave_count")!=1:
        errors.append("SUPERPORTFOLIO")
    rows={x.get("predicate_id"):x for x in residual.get("compressed_residuals",[]) if isinstance(x,dict)}
    if rows.get("FINANCE_UNCOVERED_SCOPE_AUDIT",{}).get("current_residual")!="TWO_FROZEN_DIRECT_ORACLE_LEAVES":
        errors.append("FINANCE")
    if not str(rows.get("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",{}).get("current_residual","")).startswith("TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES"):
        errors.append("UNKNOWN")
    syn=rows.get("SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",{}).get("current_residual") or {}
    if syn.get("missing_scope_relation") is not True:
        errors.append("SYNTHESIS")
    truth=composition.get("truth") or {}
    if truth.get("current_admissible_scoped_proved")!=4 or truth.get("current_open")!=8:
        errors.append("COMPOSITION")
    # Independent action-state derivation.
    scope_event_runnable = (
        oth.get("current_full_protocol_transmutation_witness_count",0)>0
        or oth.get("current_normalized_direct_reuse_closure_count",0)>0
    )
    upstream_event_runnable = truth.get("current_open",8)<8
    batches=superportfolio.get("root3_reality_fallback",{}).get("batch_classes") or []
    matched=next((x for x in batches if isinstance(x,dict) and x.get("id")=="ROOT3_MATCHED_SUPERPORTFOLIO_WAVE"),{})
    direct=next((x for x in batches if isinstance(x,dict) and x.get("id")=="ROOT3_DIRECT_ORACLE_MINCUT"),{})
    fresh_event_runnable = (
        matched.get("current_state") not in {None,"BLOCKED_BEFORE_GENERATION__EXACT_OPUS55_COMPARATOR_ADMISSIBILITY_OPEN"}
        or direct.get("current_state") not in {None,"PRESERVED_NOT_AUTHORIZED"}
    )
    runnable=sum(bool(x) for x in (scope_event_runnable,upstream_event_runnable,fresh_event_runnable))
    return errors,runnable

def main():
    candidate=load("root3_minimum_action_cut_v1.json")
    src=[
      load("root3_universal_scope_closure_activation_v1.json"),
      load("root3_target_population_coalescence_v1.json"),
      load("root3_matched_superportfolio_minimum_reality_binding_v1.json"),
      load("current_root3_zero_reality_stronger_proof_saturation_v1.json"),
      load("root3_residual_compression_v1.json"),
      load("composition_component_proof_current_authority_v6.json"),
    ]
    errors,runnable=derive(*src)
    if candidate.get("minimum_event_classes")!=[
      "NEW_SCOPE_CERTIFICATE_EVENT","UPSTREAM_SCOPE_RECEIPT_EVENT","ROOT3_FRESH_REALITY_EVENT"
    ]: errors.append("CANDIDATE_EVENT_CLASSES")
    if candidate.get("current_consequence")!="NO_NONDOMINATED_ROOT3_EXECUTION_IS_CURRENTLY_AUTHORIZED_OR_INFORMATION_POSITIVE_UNDER_BOUND_EVIDENCE__WAIT_FOR_A_RESUME_EVENT":
        errors.append("CANDIDATE_CONSEQUENCE")
    # Falsification checks: each wake event must invalidate 0-runnable conclusion.
    mutants=[]
    a,c,b,s,r,comp=src
    m=copy.deepcopy(s); m["other_live_root3_target_result"]["current_full_protocol_transmutation_witness_count"]=1
    mutants.append(("NEW_SCOPE_CERTIFICATE_EVENT",derive(a,c,b,m,r,comp)[1]>0))
    m=copy.deepcopy(comp); m["truth"]["current_admissible_scoped_proved"]=5; m["truth"]["current_open"]=7
    mutants.append(("UPSTREAM_SCOPE_RECEIPT_EVENT",derive(a,c,b,s,r,m)[1]>0))
    m=copy.deepcopy(b)
    for row in m["root3_reality_fallback"]["batch_classes"]:
        if row["id"]=="ROOT3_MATCHED_SUPERPORTFOLIO_WAVE": row["current_state"]="READY"
    mutants.append(("ROOT3_FRESH_REALITY_EVENT",derive(a,c,m,s,r,comp)[1]>0))
    if not all(ok for _,ok in mutants): errors.append("WAKE_FALSIFICATION_FAILED")
    ok=not errors and runnable==0
    out={
      "schema":SCHEMA,
      "status":"INDEPENDENT_PASS__ROOT3_11_PREDICATES_TO_3_EVENT_CLASSES__ZERO_CURRENT_RUNNABLE_EVENTS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":errors,
      "live_root3_predicates":11,
      "event_class_count":3,
      "currently_runnable_event_count":runnable,
      "wake_falsification":{k:v for k,v in mutants},
      "global_nonexistence_claimed":False,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "incremental_spend_usd":0,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
