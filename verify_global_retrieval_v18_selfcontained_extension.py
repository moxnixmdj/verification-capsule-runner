#!/usr/bin/env python3
import json, pathlib
R=pathlib.Path(__file__).resolve().parent
def load(p): return json.loads((R/p).read_text())
a=load("canonical/governance/GLOBAL_RETRIEVAL_V18_LIVE_PROVIDER_EXTENSION_ACTIVATION_V1.json")
v12=load("canonical/verification/RETRIEVAL_V12_MULTI_QUERY_RECOVERY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v13=load("canonical/verification/RETRIEVAL_V13_RESIDUAL_ROOT_FIX_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v14=load("canonical/verification/RETRIEVAL_V14_MAVEN_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v16=load("canonical/verification/RETRIEVAL_V16_GRAPH_SNOWBALL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v18=load("canonical/verification/RETRIEVAL_V18_VERSION_LINE_HISTORY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
assert a["base_current_authority"]["git_blob_sha"]=="d2f2ff3d632ab39d83f7697ecf8916690fb643c9"
assert [x["verification_git_blob_sha"] for x in a["live_provider_chain"]]==[
"59d1ff4676039c07ad5bdf2daf3e4f976265f7ba",
"2bf84eccb2119b5ae66dac65e4efe3747ad73121",
"8a436f7ba1593cb3d660f63450ec144b9fc69c27",
"3d92eca537007e38e497304d1886a4bdfcde7b88",
"13c402ded359447f32c89b4433e3c63fbe01074e",
"8b4fc08a419ed4b2f392368581f5088da5f001cc"]
for obj in (v12,v13,v14,v16,v18):
    assert obj["independent_runner"]["conclusion"]=="success"
assert v12["measured_live_truth"]["v11_plus_v12_union_hit_count"]==22
assert v13["measured_live_truth"]["v11_v12_v13_union_hit_count"]==27
assert v14["measured_live_truth"]["union_hit_count"]==28
assert v16["measured_live_truth"]["v14_plus_v16_union_hit_count"]==29
assert v18["measured_live_truth"]["v16_plus_v18_union_hit_count"]==30
assert v18["measured_live_truth"]["v16_plus_v18_union_recall"]==1.0
assert a["measured_finite_live_truth"]["best_known_union_hit_count"]==30
assert a["measured_finite_live_truth"]["best_known_union_miss_count"]==0
assert a["measured_finite_live_truth"]["open_world_recall_claim"] is False
assert "SEMANTIC_MAJOR_PARSING_MUST_IGNORE_PRERELEASE_SUFFIX_DIGITS" in a["newly_compiled_failure_immunities"]
assert a["incremental_spend_usd"]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V18_SELF_CONTAINED_LIVE_EXTENSION_VERIFIED")
