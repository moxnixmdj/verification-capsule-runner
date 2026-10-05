#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
V7 = "28940387bd6c11671035ad9201e37bba13fd9bc9"
TARGET3 = {
    "ADVANCED_AGENTIC_CODING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "BUSINESS_WORKFLOW_AUTOMATION",
}
EXPECTED_GLOBAL = {
    "ADVANCED_AGENTIC_CODING",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "COMPUTER_AND_BROWSER_USE",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "MULTI_CAPABILITY_COMPOSITION",
}
FILES = {
    "candidate": ("capsules/trajectory_critical_failure_exact_reuse_v1/brain/TRAJECTORY_CRITICAL_FAILURE_EXACT_REUSE_BINDING_20261005_V1.json", "7c41b0854149f6fa48e6de5dc369349ada027b37"),
    "registry": ("capsules/synthesis_root3_scope_relation_v1/brain/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", "ee187f611a0e82b2de495ee377682f39bc31dd31"),
    "recovery": ("capsules/trajectory_critical_failure_exact_reuse_v1/brain/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json", "981c8ac9b66ee7fccf5b531525849e29df9be483"),
    "ownership": ("capsules/trajectory_critical_failure_exact_reuse_v1/brain/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json", "4711fb5eed330990edea369725de6eaedfd3bc70"),
    "transport": ("capsules/recovery_opus55_zero_reality_v1/canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json", "95422fdb13ada158930486442c9441c9c5cd9852"),
    "scope": ("capsules/recovery_opus55_zero_reality_v1/canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_SCOPE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json", "f327bfdb5d52bb9551b52f67da14a4cd425533a3"),
    "restore": ("capsules/recovery_opus55_zero_reality_v1/canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json", "2c6bb594d353e4c6a169821da5f84a91be212ca7"),
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load_sources():
    objs = {}
    for key, (rel, expected) in FILES.items():
        p = REPO / rel
        got = git_blob_sha(p)
        if got != expected:
            raise AssertionError(f"BLOB_DRIFT:{key}:{expected}:{got}")
        objs[key] = json.loads(p.read_text(encoding="utf-8"))
    return objs

def semantic_errors(o):
    e = []
    cand=o["candidate"]; reg=o["registry"]; rec=o["recovery"]
    own=o["ownership"]; tr=o["transport"]; sc=o["scope"]; rs=o["restore"]
    def req(cond, code):
        if not cond: e.append(code)

    req(cand.get("behavior_id")==BEHAVIOR, "CANDIDATE_BEHAVIOR")
    req(cand.get("independent_verification_required") is True, "CANDIDATE_INDEPENDENCE_GUARD")
    req(all(v.get("candidate_verdict")=="PASS" for v in (cand.get("exact_reuse_obligations") or {}).values()), "CANDIDATE_OBLIGATION_VERDICTS")
    acc=cand.get("accounting") or {}
    req(all(acc.get(k)==0 for k in (
        "incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed",
        "acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"
    )), "CANDIDATE_ZERO_ACCOUNTING")

    contracts=[x for x in reg.get("active_contracted_residuals",[]) if x.get("behavior_id")==BEHAVIOR]
    req(len(contracts)==1, "REGISTRY_UNIQUE_GLOBAL_CONTRACT")
    if len(contracts)==1:
        c=contracts[0]
        req(c.get("scope")=="Failed agent trajectory to causal repair target", "CONTRACT_SCOPE")
        req(c.get("allowed_information")=="Execution receipts, tool outputs, declared constraints and admissible task evidence", "CONTRACT_AUTHORITY")
        req("earliest/critical causal failure step" in c.get("required_output_or_action",""), "CONTRACT_CAUSAL_OUTPUT")
        req("falsifiable repair target" in c.get("required_output_or_action",""), "CONTRACT_REPAIR_OUTPUT")
        req("fresh cross-domain failed trajectories" in c.get("success_condition",""), "CONTRACT_CROSS_DOMAIN_SCOPE")
        req("rescues outcome" in c.get("success_condition",""), "CONTRACT_RESCUE_SEMANTICS")
        req("downstream symptom" in c.get("failure_condition",""), "CONTRACT_NEGATIVE_CONTROL")

    fmap=reg.get("family_to_residual_contracts") or {}
    req(fmap.get("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")==[BEHAVIOR], "RECOVERY_EXACT_SINGLE_CONTRACT")
    req(all(BEHAVIOR in (fmap.get(f) or []) for f in TARGET3), "TARGET3_MAPPING")
    global_mapped={f for f,cs in fmap.items() if BEHAVIOR in (cs or [])}
    req(global_mapped==EXPECTED_GLOBAL, "GLOBAL_MAPPING_DRIFT")

    rv=rec.get("verified") or {}
    req(str(rec.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "RECOVERY_NOT_INDEPENDENT_PASS")
    req(rec.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY", "RECOVERY_FAMILY")
    req(rv.get("scope_complete") is True, "RECOVERY_SCOPE_INCOMPLETE")
    req(rv.get("objective_ceiling_or_floor") is True, "RECOVERY_NOT_OBJECTIVE_BOUND")
    req(rv.get("universal_achieved_bounds")=={
        "causal_localization":1,"terminal_recovery":1,"critical_fail_closed_misses":0
    }, "RECOVERY_BOUNDS")
    req(rv.get("historical_relation_observed_bound_used_as_proof") is False, "HISTORICAL_BOUND_USED")
    req(rv.get("historical_narrow_terminal_run_used_as_proof") is False, "NARROW_RUN_USED")
    req(rv.get("quarantined_public_recovery_run_used_as_proof") is False, "QUARANTINED_RUN_USED")
    req(rv.get("exact_opus_case_level_access_required") is False, "TARGET_ACCESS_REQUIRED")
    ei=rec.get("exact_brain_inputs") or {}
    req(ei.get("p1_universal_theorem_blob")==FILES["transport"][1], "RECOVERY_TRANSPORT_BINDING")
    req(ei.get("p1_scope_reduction_blob")==FILES["scope"][1], "RECOVERY_SCOPE_BINDING")
    req(ei.get("p1_scope_restoration_blob")==FILES["restore"][1], "RECOVERY_RESTORE_BINDING")
    req(rec.get("new_reality_units_consumed")==0 and rec.get("terminal_results_replayed")==0, "RECOVERY_REALITY_NONZERO")

    tv=tr.get("verified") or {}
    req(tr.get("behavior_id")==BEHAVIOR, "TRANSPORT_BEHAVIOR")
    req(str(tr.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "TRANSPORT_NOT_INDEPENDENT_PASS")
    req((tr.get("exact_brain_bytes") or {}).get("candidate_v7_blob")==V7, "TRANSPORT_ROUTE_BLOB")
    req(tv.get("all_v7_intervention_scorer_pass") is True, "INTERVENTION_NOT_UNIVERSAL_PASS")
    req(tv.get("all_source_native_rescue_scorer_pass") is True, "RESCUE_NOT_UNIVERSAL_PASS")
    req(tv.get("quarantined_execution_used_as_proof") is False, "TRANSPORT_QUARANTINE_USED")
    req(tv.get("new_reality_units_consumed")==0, "TRANSPORT_REALITY_NONZERO")

    sv=sc.get("verified") or {}
    req(sc.get("behavior_id")==BEHAVIOR, "SCOPE_BEHAVIOR")
    req(str(sc.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "SCOPE_NOT_INDEPENDENT_PASS")
    req(sv.get("scope_relation")=="EXACT_FROZEN_SELECTION_DOMAIN_SUBSET_OF_EXHAUSTIVE_GENERATOR_QUOTIENT", "SCOPE_RELATION")
    req(sv.get("all_three_transport_requirements_deductively_covered") is True, "SCOPE_TRANSPORT_NOT_COVERED")
    req(sv.get("remaining_failure_semantics_information_residual")==0, "SCOPE_INFORMATION_RESIDUAL")
    req(sv.get("quarantined_execution_used_as_proof") is False, "SCOPE_QUARANTINE_USED")
    req(sv.get("new_reality_units_consumed")==0 and sv.get("terminal_results_replayed")==0, "SCOPE_REALITY_NONZERO")

    rr=rs.get("verified") or {}
    req(str(rs.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "RESTORE_NOT_INDEPENDENT_PASS")
    req(rr.get("whole_p1_contract_restored") is True, "WHOLE_P1_NOT_RESTORED")
    req(rr.get("whole_scope_contract_pass_count")==12, "WHOLE_SCOPE_COUNT")
    req(rr.get("whole_scope_quarantined_contract_count")==0, "WHOLE_SCOPE_QUARANTINE")
    req(rr.get("provisional_behavioral_family_pass_count")==19, "BEHAVIORAL_ROWS")
    req(rr.get("source_fresh_reality_units_consumed")==0 and rr.get("restoration_new_reality_units_consumed")==0, "RESTORE_REALITY_NONZERO")
    req((rs.get("decisive_source") or {}).get("git_blob_sha")==FILES["scope"][1], "RESTORE_SCOPE_BINDING")

    rows=[x for x in own.get("families",[]) if x.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"]
    req(len(rows)==1, "OWNERSHIP_ROW")
    if len(rows)==1:
        r=rows[0]
        req(r.get("acceptance")=="PASS", "OWNERSHIP_ACCEPTANCE")
        req((r.get("acceptance_receipt") or {}).get("git_blob_sha")==FILES["recovery"][1], "OWNERSHIP_RECOVERY_BINDING")
        scope_hashes={x.get("git_blob_sha") for x in r.get("scope_receipts",[])}
        req(FILES["transport"][1] in scope_hashes and FILES["restore"][1] in scope_hashes, "OWNERSHIP_SCOPE_BINDINGS")
        req((r.get("operative_artifact") or {}).get("git_blob_sha")==V7, "OWNERSHIP_ROUTE_BLOB")
        req((r.get("operative_artifact") or {}).get("path")=="canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py", "OWNERSHIP_ROUTE_PATH")
        req(r.get("exact_receipt_binding") is True, "OWNERSHIP_EXACT_BINDING")
        req(r.get("external_target_capability_provider") is False, "OWNERSHIP_EXTERNAL_PROVIDER")
        req(r.get("forbidden_provider_or_escape_hits")==[], "OWNERSHIP_ESCAPE_HITS")
        req(r.get("promotion")=="VERIFIED_OWNED_EQUAL_OR_BETTER", "OWNERSHIP_PROMOTION")
    req(own.get("promotion_authority") is True, "OWNERSHIP_AUTHORITY")

    th=cand.get("theorem") or {}
    req(set(th.get("affected_families") or [])==TARGET3, "CANDIDATE_TARGET3")
    req(th.get("discharged_family_local_slots_if_verified")==3, "CANDIDATE_SLOT_COUNT")
    req(th.get("discharged_unique_contracts_if_verified")==1, "CANDIDATE_UNIQUE_COUNT")
    req(th.get("remaining_unique_contracts_in_five_family_cut_if_verified")==9, "CANDIDATE_REMAINING_COUNT")
    return sorted(set(e))

def evaluate(objs):
    errors=semantic_errors(objs)
    global_mapped=sorted(
        f for f,cs in (objs["registry"].get("family_to_residual_contracts") or {}).items()
        if BEHAVIOR in (cs or [])
    )
    return {
        "pass": not errors,
        "errors": errors,
        "behavior_id": BEHAVIOR,
        "critical_path_families": sorted(TARGET3),
        "global_mapped_families": global_mapped,
        "global_family_slot_count": len(global_mapped),
        "additional_family_slots_beyond_already_accepted_recovery": max(0,len(global_mapped)-1),
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "promotion_authority": False,
    }

def self_test(base):
    cases=[]
    a=copy.deepcopy(base); a["ownership"]["families"][1]["external_target_capability_provider"]=True
    cases.append(("external_provider", evaluate(a)["pass"] is False))
    b=copy.deepcopy(base); b["recovery"]["verified"]["scope_complete"]=False
    cases.append(("scope_incomplete", evaluate(b)["pass"] is False))
    c=copy.deepcopy(base); c["registry"]["family_to_residual_contracts"]["ADVANCED_AGENTIC_CODING"].remove(BEHAVIOR)
    cases.append(("mapping_removed", evaluate(c)["pass"] is False))
    d=copy.deepcopy(base); d["transport"]["exact_brain_bytes"]["candidate_v7_blob"]="0"*40
    cases.append(("route_drift", evaluate(d)["pass"] is False))
    if not all(ok for _,ok in cases):
        raise AssertionError("SELF_TEST_FAILURE:"+repr(cases))
    return cases

if __name__=="__main__":
    src=load_sources()
    out=evaluate(src)
    print(json.dumps(out,indent=2,sort_keys=True))
    if not out["pass"]:
        raise SystemExit(1)
    print("FAIL_CLOSED_SELF_TESTS", self_test(src))
