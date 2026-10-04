#!/usr/bin/env python3
import json
from pathlib import Path
from canonical.runtime import retrieval_v20_miss_recovery_v1 as recovery

ROOT=Path(__file__).resolve().parent

# The original fresh holdout truth is immutable and must precede repair evidence.
receipt_path=ROOT/"canonical/verification/RETRIEVAL_V20_FRESH_HOLDOUT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
truth=receipt["measured_live_truth"]
assert truth["case_count"]==12
assert truth["usable_case_count"]==12
assert truth["hit_count"]==8
assert truth["miss_count"]==4
assert truth["portfolio_union_recall_on_usable_cases"]==8/12
assert truth["miss_episode_ids"]==[
    "H20_GITHUB_RUST_SEARCH",
    "H20_GITHUB_AR_NLP",
    "H20_MAVEN_LANG_UTIL",
    "H20_RUBY_JOBS",
]

out=recovery.run(root=ROOT,timeout=20.0)
assert out["frozen_original_holdout_recall"]==8/12
assert out["miss_case_count"]==4
assert out["original_v20_result_reclassified"] is False
assert out["answer_key_loaded_only_after_all_retrieval_execution"] is True
assert out["answer_key_identity_used_for_query_generation"] is False

print("V20_POST_HOLDOUT_REPAIR_SUMMARY="+json.dumps({
    "schema":out["schema"],
    "status":out["status"],
    "original_holdout_recall":out["frozen_original_holdout_recall"],
    "miss_case_count":out["miss_case_count"],
    "recovered_count":out["recovered_count"],
    "recovery_rate":out["recovery_rate"],
    "remaining_miss_episode_ids":out["remaining_miss_episode_ids"],
    "cases":out["cases"],
    "open_world_completeness_claim":out["open_world_completeness_claim"],
},sort_keys=True))
