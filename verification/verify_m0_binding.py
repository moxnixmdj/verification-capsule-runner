import json
from pathlib import Path

p=Path("verification/m0_binding.json")
d=json.loads(p.read_text())
errors=[]
if d.get("behavior_id")!="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001": errors.append("BEHAVIOR_ID")
if d.get("proof_mode")!="PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN_TERMINAL_PROOF": errors.append("PROOF_MODE")
if set(d.get("portfolio_bindings",[]))!={"T0","T1","T2","T3"}: errors.append("PORTFOLIOS")
forbidden={"HIDDEN_VERIFIER","REFERENCE_SOLUTION","GOLD_NORMALIZED_REQUIREMENTS","GOLD_ACCEPTANCE_CONSEQUENCES","MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON"}
if set(d.get("candidate_visible_information",[])) & forbidden: errors.append("ORACLE_LEAK")
if not forbidden <= set(d.get("candidate_must_not_receive",[])): errors.append("FORBIDDEN_SET")
required={"DROP_REQUIRED_ATOM","INVERT_REQUIREMENT_POLARITY","DELETE_MATERIAL_CONDITION","COLLAPSE_AMBIGUITY_TO_ARBITRARY_SINGLE_INTERPRETATION","REMOVE_INDEPENDENT_ACCEPTANCE_FAILURE_MODE"}
if set(d.get("evaluator",{}).get("required_mutations",[]))!=required: errors.append("MUTATIONS")
ta=d.get("terminal_acceptance",{})
if ta.get("prewave_binding_is_terminal_result") is not False: errors.append("PREWAVE_CREDIT")
if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True: errors.append("SYNTHETIC_OVERCLAIM")
if ta.get("terminal_evidence_source")!="THE_FROZEN_T0_T1_T2_T3_OBSERVATIONS": errors.append("EVIDENCE_SOURCE")
for k,v in d.get("contamination",{}).items():
    if v is not False: errors.append("CONTAMINATION:"+k)
if d.get("execution_authority") is not False: errors.append("AUTHORITY")
if d.get("terminal_results_observed")!=0: errors.append("RESULTS")
if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0: errors.append("CREDIT")
expected_blobs={
"brain_blob_sha":"33f0efd1407b36211d40908d97b63fae571fb50f",
"brain_preflight_blob_sha":"f57482627eea74e6d0f06d4ac7579e02eced4ab5",
"brain_test_blob_sha":"e902e8bf6fd34c7a33f32d488bcd9ba7d57c020a"}
for k,v in expected_blobs.items():
    if d.get(k)!=v: errors.append("BLOB:"+k)
print(json.dumps({"pass":not errors,"errors":errors},sort_keys=True))
raise SystemExit(1 if errors else 0)
