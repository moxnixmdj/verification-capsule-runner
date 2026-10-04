import json
from pathlib import Path
load=lambda n: json.loads(Path("verification_inputs",n).read_text())

act=load("osworld_methodology_activation.json")
rec=load("osworld_methodology_receipt.json")
cand=load("osworld_methodology_candidate.json")
gitlab=load("osworld_gitlab_sept10.json")
gitlab_rec=load("osworld_gitlab_sept10_receipt.json")

assert act["schema"]=="PROJECT_BRAIN_OSWORLD_OPUS55_PRIMARY_METHODOLOGY_ACTIVATION_V1"
assert act["target_predicate"]=="OSWORLD_2_1_PARTIAL_GE_81_8"
assert act["methodology"]["git_blob_sha"]=="f4bc47440829387db14e37c900a269d11f77fdc1"
assert act["verification"]["git_blob_sha"]=="b1d9b9fb008807415b1c2a0248380c005765d9e8"

assert rec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert rec["independent_runner"]["workflow_run_id"]==37169557068
assert rec["independent_runner"]["workflow_job_id"]==111339544751
assert rec["independent_runner"]["conclusion"]=="success"
v=rec["verified"]
assert v["opus55_partial_score_percent"]==81.8
assert v["opus55_strict_pass_rate_percent"]==48.7
assert v["task_count"]==108
assert v["partial_mean_per_task_weighted_checkpoint_credit"] is True
assert v["strict_pass_requires_all_checkpoints"] is True
assert v["pass_at_1_averaged_over_five_independent_runs"] is True
assert v["resolution"]=="1080p"
assert v["max_action_steps_per_task"]==500
assert v["reasoning_effort"]=="MAXIMUM"
assert v["model_grader"]=="Claude Opus 4.8"
assert v["source_update_date"]=="2026-09-10"
assert v["retain_all_screenshots"] is True
assert v["server_side_context_compaction_after_tokens"]==100000
assert v["launch_row_label"]=="OSWorld 2.1"
assert v["anthropic_exact_v21_component_hash_identity_proved"] is False

expected={
 "UNKNOWN_ANTHROPIC_TASK_COUNT",
 "UNKNOWN_PARTIAL_SCORING_DEFINITION",
 "UNKNOWN_STRICT_SCORING_DEFINITION",
 "UNKNOWN_NUMBER_OF_RUNS",
 "UNKNOWN_SCREEN_RESOLUTION",
 "UNKNOWN_MAX_ACTION_STEPS",
 "UNKNOWN_MODEL_GRADER_IDENTITY",
 "UNKNOWN_SCREENSHOT_RETENTION_POLICY",
 "UNKNOWN_CONTEXT_COMPACTION_THRESHOLD",
}
assert set(act["delete"])==expected
assert set(rec["scheduler_deletions"])==expected

pres=set(act["preserve"])
assert "EXACT_SEPTEMBER_10_SOURCE_TO_OSWORLD_V21_RELEASE_IDENTITY_RELATION_UNLESS_INDEPENDENTLY_PROVED" in pres
assert "MATERIAL_HUGGINGFACE_ACCESS_TO_PINNED_TASKS_AND_ASSETS" in pres
assert "SELF_HOST_WEBSITE_AND_GITLAB_FUNCTIONAL_REACHABILITY" in pres
assert "ZERO_COST_OR_PROVED_EQUIVALENT_CLAUDE_OPUS_4_8_MODEL_GRADER_ROUTE_FOR_GRADER_TASKS" in pres
assert "BRAIN_SCORE_GE_81_8_PARTIAL" in pres

# Complementary GitLab state narrows public revision search but cannot prove Anthropic identity.
assert gitlab["public_state"]["latest_commit_at_or_before_2026_09_10"]=="8655d651722f4254e59e813de9f68a6732ea525c"
assert gitlab["verified_if_passes"]["delete"]=="GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH"
assert "ANTHROPIC_USED_THIS_EXACT_REVISION_OR_EQUIVALENT_STATE" in gitlab["still_open"]
assert gitlab_rec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert gitlab_rec["verified"]["generic_public_revision_discovery_deletable"] is True
assert gitlab_rec["verified"]["anthropic_exact_revision_identity_proved"] is False

assert "NO_CLAIM_SYSTEM_CARD_LABEL_OSWORLD_2_0_EQUALS_RELEASE_TAG_OSWORLD_V2_1" in cand["hard_nonclaims"]
assert "NO_CLAIM_ANTHROPIC_USED_EXACT_V21_ASSET_AND_WEBSITE_HASHES_UNTIL_VERIFIED" in cand["hard_nonclaims"]
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
print("OSWORLD_OPUS55_PRIMARY_METHODOLOGY_ACTIVATION: PASS")
