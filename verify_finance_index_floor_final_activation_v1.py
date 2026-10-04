import json
from pathlib import Path
load=lambda n: json.loads(Path("verification_inputs",n).read_text())
final=load("finance_floor_final_activation.json")
actrec=load("finance_floor_activation_receipt.json")
floorrec=load("finance_floor_receipt.json")

assert final["schema"]=="PROJECT_BRAIN_FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_FINAL_ACTIVATION_V1"
assert final["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert final["activation_candidate"]["git_blob_sha"]=="73ca9026ec6db04c062319da557e4b1fa943c06c"
assert final["activation_verification"]["git_blob_sha"]=="29954b415f94b4cae9857607326e1a656a63f706"
assert actrec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert actrec["independent_runner"]["workflow_run_id"]==37174586300
assert actrec["independent_runner"]["workflow_job_id"]==111354452161
assert actrec["independent_runner"]["conclusion"]=="success"
assert floorrec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert floorrec["verified"]["all_eight_underlying_evaluation_floors_zero"] is True
assert floorrec["verified"]["finance_capability_subscore_floor_proved"] is False

expected={
 "GENERIC_SEARCH_FOR_NEGATIVE_RANGES_OF_FINANCE_UNDERLYING_EVALUATIONS",
 "REPROVE_NONNEGATIVITY_OF_THE_EIGHT_LISTED_EVALUATION_SCALES",
}
assert set(final["delete"])==expected
assert final["zero_floor_substitution_authorized"] is False
assert "CAPABILITY_SUBSCORE_AGGREGATION_OR_NORMALIZATION_TRANSFORM" in final["preserve"]
assert "INDEPENDENTLY_VERIFIED_BRAIN_COMPONENT_LOWER_BOUNDS" in final["preserve"]
assert "EXISTING_ARTIFICIAL_ANALYSIS_OWNER_CHANNEL_RESULT" in final["preserve"]
assert "DIRECT_THRESHOLD_WEIGHTED_LOWER_BOUND_GE_61" in final["preserve"]
assert final["authority"]=={
 "scheduling":True,
 "effective_scheduling":True,
 "execution":False,
 "promotion":False,
 "fresh_reality":False,
}
assert final["accounting"]=={
 "incremental_spend_usd":0,
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
}
print("FINANCE_INDEX_FLOOR_FINAL_ACTIVATION: PASS")
