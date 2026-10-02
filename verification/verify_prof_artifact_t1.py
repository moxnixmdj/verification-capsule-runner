import json
from pathlib import Path
d=json.loads(Path("verification/prof_artifact_t1_binding.json").read_text())
errors=[]
if d.get("brain_blob_sha")!="a14dfa69257eaa29e51f3045d7f49907b1bb3be8":errors.append("BLOB")
if d.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":errors.append("BEHAVIOR")
if d.get("proof_mode")!="T1_MULTIPLEXED_DIRECT_PROFESSIONAL_QUALITY_GATE":errors.append("MODE")
dec=d.get("decomposition") or {}
if dec.get("reused_adjacent_gate")!="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":errors.append("NATIVE_GATE")
if dec.get("no_cross_behavior_score_inheritance") is not True:errors.append("CROSS_CREDIT")
vis=set(d.get("candidate_visible_information") or []); hidden=set(d.get("hidden_evaluator_information") or [])
if vis & hidden:errors.append("VISIBLE_HIDDEN_OVERLAP")
for x in ["HIDDEN_ORACLE_FACTORS","REFERENCE_SOLUTION","GOLD_PLAN","ABLATION_LABELS","EXPECTED_SCORE_DELTA","TERMINAL_ACCEPTANCE_LABEL"]:
    if x not in d.get("candidate_must_not_receive",[]):errors.append("FORBIDDEN:"+x)
ts=d.get("terminal_surface") or {}
if ts.get("portfolio")!="T1":errors.append("PORTFOLIO")
if ts.get("synthetic_whole_domain_superset_required") is not False:errors.append("OVERCLAIM")
if ts.get("named_private_benchmarks_required_for_execution") is not False:errors.append("PRIVATE_DEP")
need={"SELECTED_EDIT_IDS_EXIST_AND_EDIT_BUDGET_IS_RESPECTED","EVERY_SELECTED_CLAIM_IS_TRACEABLE_TO_VISIBLE_SOURCE_FACTS","SUPPORTED_REQUIRED_TOPICS_ARE_NOT_SILENTLY_DROPPED","AUDIENCE_AND_ANALYSIS_KIND_ARE_LOAD_BEARING","INDEPENDENT_RUBRIC_DELTA_BEATS_MECHANICS_ONLY_BASELINE_WHEN_QUALITY_JUDGMENT_IS_LOAD_BEARING","SEEDED_PLAN_ABLATION_DEGRADES_OR_FAILS_THE_RELEVANT_RUBRIC_DIMENSION","SEEDED_RESCUE_EDIT_RESTORES_OR_IMPROVES_THE_RELEVANT_RUBRIC_DIMENSION","ANY_NATIVE_EDIT_USED_BY_THE_CASE_PASSES_THE_SEPARATE_NATIVE_ARTIFACT_MECHANICAL_GATE"}
if not need <= set(d.get("direct_instrumentation") or []):errors.append("INSTRUMENTATION")
pa=d.get("post_freeze_accounting") or {}
for k in ["adaptive_case_selection","case_replacement","tuning_replay","result_to_runtime_feedback_during_wave","oracle_or_threshold_edit_after_first_terminal_result"]:
    if pa.get(k) is not False:errors.append("FREEZE:"+k)
if pa.get("failed_case_counts_as_failure") is not True:errors.append("FAIL_DISPOSITION")
if d.get("prewave_admissible") is not False:errors.append("PREMATURE_ADMISSION")
if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0:errors.append("AUTHORITY")
if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0:errors.append("CREDIT")
print(json.dumps({"pass":not errors,"errors":sorted(set(errors))},sort_keys=True))
raise SystemExit(1 if errors else 0)
