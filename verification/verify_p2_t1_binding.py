import json
from pathlib import Path
d=json.loads(Path("verification/p2_t1_binding.json").read_text())
errors=[]
if d.get("brain_blob_sha")!="1101b7f2d18d938bed8f430659b5fab3f9ef99a5":errors.append("BLOB")
if d.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":errors.append("BEHAVIOR")
if d.get("portfolio_bindings")!=["T1"]:errors.append("PORTFOLIO")
expected={"T1/GDPVAL_AA_V2_1::P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF","T1/AA_BRIEFCASE_V1_1::P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF"}
if set(d.get("direct_surface_bindings",[]))!=expected:errors.append("SURFACES")
ps=d.get("private_surface_rule") or {}
if ps.get("official_private_elo_reproduction_required") is not False or ps.get("private_score_inference_forbidden") is not True:errors.append("PRIVATE_SCORE_RULE")
ib=d.get("information_boundary") or {}
if ib.get("candidate_receives_hidden_oracle") is not False or ib.get("candidate_receives_reference_solution") is not False:errors.append("ORACLE_BOUNDARY")
if set(ib.get("candidate_visible",[])) & set(ib.get("hidden_oracle",[])):errors.append("VISIBLE_HIDDEN_OVERLAP")
ev=d.get("evaluator") or {}
for x in ["REMOVE_REQUIRED_ANALYSIS","INSERT_UNSUPPORTED_POLISHED_CLAIM","SWAP_AUDIENCE_PRIORITY","OBSCURE_KEY_INFORMATION","BREAK_NATIVE_STRUCTURE"]:
    if x not in ev.get("mutations",[]):errors.append("MUTATION:"+x)
ta=d.get("terminal_acceptance") or {}
if ta.get("prewave_binding_is_terminal_result") is not False:errors.append("PREWAVE_CREDIT")
if ta.get("standalone_private_benchmark_reproduction_required") is not False:errors.append("PRIVATE_REPRO")
if ta.get("synthetic_whole_open_domain_superset_claim_forbidden") is not True:errors.append("OPEN_DOMAIN_OVERCLAIM")
pop=d.get("population_selection") or {}
for k in ["adaptive_case_selection","case_replacement","tuning_replay"]:
    if pop.get(k) is not False:errors.append("SELECTION:"+k)
if pop.get("no_result_seen_before_freeze") is not True:errors.append("FREEZE")
if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0:errors.append("AUTHORITY")
if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0:errors.append("CREDIT")
print(json.dumps({"pass":not errors,"errors":sorted(set(errors))},sort_keys=True))
raise SystemExit(1 if errors else 0)
