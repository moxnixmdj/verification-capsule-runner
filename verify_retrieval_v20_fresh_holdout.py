#!/usr/bin/env python3
import json
from pathlib import Path
from canonical.runtime import retrieval_verified_route_executor_v1 as executor
from canonical.runtime import retrieval_fresh_holdout_arena_v20 as arena

ROOT=Path(__file__).resolve().parent

# Exact frozen bytes.
EXPECTED={
 "canonical/runtime/retrieval_verified_route_executor_v1.py":"dd1b4dfb8f2412867650c8a546285e38f3b1b9ee",
 "canonical/governance/RETRIEVAL_V20_FRESH_HOLDOUT_MANIFEST_V1.json":"b9f1798b7c5d745b0f71aa5a09f8404545129004",
 "canonical/governance/RETRIEVAL_V20_FRESH_HOLDOUT_ANSWER_KEY_V1.json":"4a3d7406a23149f8aef66aa0ad04ce3b0b56a61c",
 "canonical/runtime/retrieval_fresh_holdout_arena_v20.py":"03e9e6f2dd0f87f0c86ee18474d6620b7a1b7e4d",
 "canonical/tests/test_retrieval_fresh_holdout_arena_v20.py":"0f7439b7359fe69fb314707cb9120346117bac0c",
}
for rel,sha in EXPECTED.items():
    got=arena._blob((ROOT/rel).read_bytes())
    assert got==sha,(rel,got,sha)

# Training-case preflight only. These targets belong to the old V11 labeled set,
# not the fresh holdout. The executor still receives no target.
preflight=executor.execute_request(
    root=ROOT,
    query_action={
        "action_id":"PREFLIGHT_V11_JSON_CLI",
        "source_id":"GITHUB_REPOSITORY_SEARCH",
        "query_family":"PREFLIGHT_ONLY",
        "query":"command line JSON processor filter transform",
    },
    source={
        "source_id":"GITHUB_REPOSITORY_SEARCH",
        "provider":"github",
        "upstream_group":"GITHUB_PUBLIC_API",
        "source_class":"repository",
        "script":"LATIN",
    },
    timeout=15.0,
)
assert preflight["status"]=="LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE",preflight
assert preflight["planned_action_count"]>0
assert preflight["answer_key_identity_used"] is False
print("V20_PREFLIGHT_PASS="+json.dumps({
    "planned_action_count":preflight["planned_action_count"],
    "candidate_count":preflight["candidate_count"],
},sort_keys=True))

# First fresh holdout execution.
out=arena.run(root=ROOT,timeout=20.0)
m=out["measurement"]
assert out["answer_key_loaded_only_after_all_retrieval_execution"] is True
assert out["answer_key_identity_used_for_query_generation"] is False
assert out["answer_key_identity_used_for_route_generation"] is False
assert out["answer_key_identity_used_for_provider_selection"] is False
assert m["case_count"]==12
assert m["usable_case_count"]>0

print("V20_FRESH_HOLDOUT_SUMMARY="+json.dumps({
    "schema":out["schema"],
    "status":out["status"],
    "executor_git_blob_sha":out["executor_git_blob_sha"],
    "case_count":m["case_count"],
    "usable_case_count":m["usable_case_count"],
    "failed_retryable_case_count":m["failed_retryable_case_count"],
    "hit_count":m["hit_count"],
    "miss_count":m["miss_count"],
    "portfolio_union_recall_on_usable_cases":m["portfolio_union_recall_on_usable_cases"],
    "miss_episode_ids":m["miss_episode_ids"],
    "failed_episode_ids":m["failed_episode_ids"],
    "mean_first_hit_action_index":m["mean_first_hit_action_index"],
    "mean_first_hit_measured_route_latency_seconds":m["mean_first_hit_measured_route_latency_seconds"],
    "difficulty_metrics":m["difficulty_metrics"],
    "provider_metrics":m["provider_metrics"],
    "cases":m["cases"],
    "open_world_completeness_claim":out["open_world_completeness_claim"],
},ensure_ascii=False,sort_keys=True))
