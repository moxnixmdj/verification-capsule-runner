import json
from pathlib import Path
R=Path(__file__).resolve().parent/"brain"
res=json.loads((R/"canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json").read_text())
paths=[
"canonical/verification/UNIVERSAL_SCOPE_CLOSURE_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
"canonical/verification/ROOT3_UNIVERSAL_SCOPE_CLOSURE_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
"canonical/verification/ROOT3_TARGET_POPULATION_COALESCENCE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
"canonical/verification/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
for p in paths:
    x=json.loads((R/p).read_text())
    assert x["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),(p,x["status"])
    assert x["new_reality_units_consumed"]==0
    assert x["fresh_reality_authority"] is False
f=res["optimized_execution_frontier"]
assert f["live_root3_involved_predicates"]==11
assert f["work_classes"]==4
assert f["formal_scope_targets"]==7
assert f["formal_target_population_identities"]==4
assert f["duplicate_population_definition_actions_eliminated"]==3
assert f["matched_scope_targets"]==8
assert f["future_shared_superportfolio_waves"]==1
assert f["frozen_direct_oracle_leaves"]==4
assert f["empirical_fallback_batch_classes"]==2
assert f["current_root3_predicates_closed_by_these_optimizations"]==0
assert f["current_fresh_reality_authority"] is False
a=res["authority"]
assert a["generic_scope_certificate_compiler"]["verification_git_blob_sha"]=="27a791738a7dedc2fd9634f2e13356bdc2d8f766"
assert a["root3_frontier_compiler"]["verification_git_blob_sha"]=="539c2702bb6d06151228461db0138a74a732240c"
assert a["target_population_coalescence"]["verification_git_blob_sha"]=="fe2da7ca39e9630bfdd0c1de414c0c3e2543ced9"
assert a["matched_superportfolio_mincut"]["verification_git_blob_sha"]=="6621a42641a1bc939892c00eaca63b7d4f664d47"
print("ROOT3_CURRENT_FRONTIER_V2_INDEPENDENT_PASS")
