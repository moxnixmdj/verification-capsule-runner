#!/usr/bin/env python3
import json, pathlib, math
ROOT=pathlib.Path(__file__).resolve().parent
candidate=json.loads((ROOT/"subject/livebench_local_root1_20261004/candidate.json").read_text())
source=json.loads((ROOT/"subject/livebench_v6_forced_fail_20261004/reconciliation.json").read_text())
assert candidate["schema"]=="PROJECT_BRAIN_LIVEBENCH_LOCAL_ROOT_RECLASSIFICATION_V1"
assert candidate["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert source["schema"]=="PROJECT_BRAIN_LIVEBENCH_REPLAY72_V6_FORCED_FAIL_RECONCILIATION_V1"
assert source["target_predicate"]==candidate["target_predicate"]
assert candidate["frozen_candidate"]=={"commit":source["frozen_candidate"]["commit"],"tree":source["frozen_candidate"]["tree"]}
obs=source["observed"]; proof=source["threshold_proof"]; ev=candidate["evidence"]
assert obs["replay_prefix_count"]==72 and obs["unique_question_ids"]==72
assert obs["observed_score_mass"]==0
assert proof["population_count"]==200 and proof["unobserved_remaining_count"]==128
assert proof["conservative_full_population_upper_percent"]==64
assert proof["threshold_percent"]==65.7
assert proof["predicate_pass_mathematically_possible_for_frozen_candidate"] is False
assert proof["further_case_exposure_required_to_decide_predicate_for_frozen_candidate"] is False
assert abs((128/200*100)-64.0)<1e-12 and 64.0<65.7
assert ev["verified_observed_zero_score_cases"]==72
assert ev["maximum_remaining_score_mass"]==128
assert ev["full_population_upper_percent"]==64.0
assert ev["threshold_percent"]==65.7
cc=source["classification_candidate"]
assert cc["root2_measurement_uncertainty_for_this_frozen_candidate"]=="RESOLVED_NEGATIVELY"
assert cc["acceptance_predicate_state_for_this_frozen_candidate"]=="PROVED_FALSE"
assert cc["constructive_operational_failure_observed"] is True
assert cc["proposed_root_reclassification"].startswith("ROOT1_POSITIVE_OPERATIVE_CAPABILITY_OR_CONFIGURATION_GAP")
snap=candidate["authority"]["root_state_snapshot"]
assert snap["livebench_prior_membership"]=="ROOT2_ONLY"
assert snap["root1_positive_gap_count"]==0
rt=candidate["root_transition"]
assert rt["prior_local_class"].startswith("ROOT2_ONLY")
assert rt["new_local_class"].startswith("ROOT1_POSITIVE_OPERATIVE_GAP")
assert rt["root2_local_residual"] is False
assert rt["root3_local_residual"] is False
assert rt["root1_positive_gap"] is True
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
assert candidate["fresh_reality_authority"] is False
for k,v in candidate["accounting"].items():
    if k.endswith("_delta") or k in ("incremental_spend_usd","new_terminal_cases_exposed"):
        assert v==0
print("PASS:LIVEBENCH_LOCAL_ROOT1_RECLASSIFICATION_V1")
