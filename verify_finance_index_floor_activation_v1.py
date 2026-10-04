import json
from pathlib import Path

def load(n):
    return json.loads(Path("verification_inputs", n).read_text())

act=load("finance_floor_activation.json")
rec=load("finance_floor_receipt.json")
sat=load("finance_public_transform_saturation.json")

assert act["schema"]=="PROJECT_BRAIN_FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_ACTIVATION_V1"
assert act["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert act["boundary"]=={
    "path":"canonical/governance/FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_20261004_V1.json",
    "git_blob_sha":"277feb222baaa87526a17ac846d16413b31df44a",
}
assert act["verification"]=={
    "path":"canonical/verification/FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "git_blob_sha":"4b34bdca9c990a8bacdca78b2a1c6f9ae0170c3b",
}
assert rec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert rec["independent_runner"]["pull_request"]==1658
assert rec["independent_runner"]["workflow_run_id"]==37174344308
assert rec["independent_runner"]["workflow_job_id"]==111353729622
assert rec["independent_runner"]["conclusion"]=="success"
assert rec["verified"]["underlying_evaluation_floor_count"]==8
assert rec["verified"]["all_eight_underlying_evaluation_floors_zero"] is True
assert rec["verified"]["finance_capability_subscore_floor_proved"] is False
assert rec["verified"]["zero_floor_substitution_authorized"] is False
assert rec["verified"]["hidden_capability_subscore_transform_proved"] is False
assert rec["verified"]["brain_component_score_proved"] is False
assert rec["verified"]["finance_index_score_proved"] is False

expected={
 "GENERIC_SEARCH_FOR_NEGATIVE_RANGES_OF_FINANCE_UNDERLYING_EVALUATIONS",
 "REPROVE_NONNEGATIVITY_OF_THE_EIGHT_LISTED_EVALUATION_SCALES",
}
assert set(act["delete"])==expected
assert set(rec["scheduler_deletions"])==expected
assert act["zero_floor_substitution_authorized"] is False
assert "CAPABILITY_SUBSCORE_AGGREGATION_OR_NORMALIZATION_TRANSFORM" in act["preserve"]
assert "INDEPENDENTLY_VERIFIED_BRAIN_COMPONENT_LOWER_BOUNDS" in act["preserve"]
assert "EXISTING_ARTIFICIAL_ANALYSIS_OWNER_CHANNEL_RESULT" in act["preserve"]
assert "DIRECT_THRESHOLD_WEIGHTED_LOWER_BOUND_GE_61" in act["preserve"]

# Complementary route saturation must preserve the same irreducible residual.
assert sat["exact_deduction"]["finance_subscore_zero_floor_proved"] is False
assert sat["exact_deduction"]["public_free_api_documented_inner_capability_transform"] is False
assert sat["exact_deduction"]["direct_threshold_predicate_closed"] is False
assert "SEPARATELY_ADMISSIBLE_FORMAL_LOWER_BOUND_ON_CAPABILITY_SUBSCORES" in sat["scheduler_effect_if_independently_verified"]["preserve"]
assert "NO_ZERO_FLOOR_INFERENCE" in sat["hard_nonclaims"]

assert act["authority"]=={
 "scheduling":False,
 "effective_scheduling":False,
 "execution":False,
 "promotion":False,
 "fresh_reality":False,
}
assert act["accounting"]==rec["accounting"]=={
 "incremental_spend_usd":0,
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
}
print("FINANCE_INDEX_FLOOR_ACTIVATION_CANDIDATE: PASS")
