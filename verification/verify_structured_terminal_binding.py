import json
from pathlib import Path
d=json.loads(Path("verification/structured_terminal_binding.json").read_text())
o=d["outer"]; p=d["population"]; errors=[]
if d["brain_blobs"]["outer"]!="6d2e9adbd45af41c26c543f69769a6f9c69d52ac":errors.append("OUTER_BLOB")
if d["brain_blobs"]["population"]!="95372e0359225a4e10e8eaeff51c6f99f1601253":errors.append("POP_BLOB")
if o.get("behavior_id")!="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":errors.append("BEHAVIOR")
if o.get("portfolio_bindings")!=["T0","T1"]:errors.append("PORTFOLIOS")
expected_surfaces={"T0/FRONTIERCODE_V1_1::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF","T1/FINANCE_ACCOUNTING_INDEX::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF","T1/FINANCE_AGENT_V2::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF"}
if set(o.get("direct_surface_bindings",[]))!=expected_surfaces:errors.append("SURFACES")
for f in ["HIDDEN_VERIFIER","REFERENCE_GRAPH","GOLD_REQUIREMENT_LINEAGE","GOLD_JUSTIFIED_EXCLUSIONS","GOLD_EDGE_ACCEPTANCE_RESULT","MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON"]:
    if f not in o.get("candidate_must_not_receive",[]):errors.append("FORBIDDEN:"+f)
    if f in o.get("candidate_visible_information",[]):errors.append("LEAK:"+f)
ta=o.get("terminal_acceptance",{})
if ta.get("prewave_binding_is_terminal_result") is not False:errors.append("PREWAVE_CREDIT")
if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:errors.append("OVERCLAIM")
if ta.get("terminal_evidence_source")!="THE_FROZEN_T0_T1_TERMINAL_OBSERVATIONS":errors.append("TERMINAL_SOURCE")
if p.get("proof_mode")!="THEORETICAL_CEILING_OR_MACHINE_CHECKED_FORMAL_PROOF":errors.append("POP_MODE")
pop=p.get("population",{})
if pop.get("sample_count")!=2000:errors.append("POP_COUNT")
for k in ["adaptive_case_selection","case_replacement","replay_for_tuning"]:
    if pop.get(k) is not False:errors.append("POP_"+k)
if pop.get("post_freeze_beacon") is not None:errors.append("BEACON")
if p.get("acceptance",{}).get("allowed_failed_cases")!=0:errors.append("FAIL_ALLOWANCE")
if p.get("scope_gate",{}).get("status")!="INDEPENDENT_PASS__ADMISSIBLE_SUBSTITUTION__ZERO_UNRESOLVED_DIMENSIONS":errors.append("SCOPE_GATE")
if p.get("boundary",{}).get("target_weakened") is not False:errors.append("TARGET_WEAKENED")
if p.get("information_boundary",{}).get("candidate_receives_hidden_oracle") is not False:errors.append("ORACLE_VISIBLE")
for obj in [o,p]:
    if obj.get("execution_authority") is not False or obj.get("terminal_results_observed")!=0:errors.append("AUTHORITY_OR_RESULTS")
    if obj.get("capability_credit_delta")!=0 or obj.get("family_credit_delta")!=0:errors.append("CREDIT")
print(json.dumps({"pass":not errors,"errors":sorted(set(errors))},sort_keys=True))
raise SystemExit(1 if errors else 0)
