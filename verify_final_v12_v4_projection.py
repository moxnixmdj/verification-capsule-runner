#!/usr/bin/env python3
import json
from pathlib import Path

B=Path("subject/final_v12_v4_projection_20261004_sol")
a=json.loads((B/"AUTHORITY.json").read_text())
r=json.loads((B/"ROOT_STATE.json").read_text())

ROOT="f61fa58c7bef6dca90758bc0135536b7676386e9"
for key in ("terminal_root_cause_state","terminal_root_cause_state_v1"):
    assert a["sources"][key]["git_blob_sha"]==ROOT

assert a["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert a["truth"]["opus55_verified_owned"]=="5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN"
assert a["truth"]["achieved"] is False

assert r["current_acceptance"]["accepted_families"]==5
assert r["current_acceptance"]["proved_atomic"]==12
assert r["current_acceptance"]["unresolved_atomic"]==26
assert r["current_acceptance"]["terminal"] is False

r2=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12.json"
assert r2["current_frontier_git_blob_sha"]=="75ca9127a73ca2dd52a49f2f09e2e0ccc384129a"
assert r2["current_frontier_verification_git_blob_sha"]=="c13903bb6b0f2b03f934664e2af77fdc4cc0696b"
assert r2["current_frontier_activation_git_blob_sha"]=="f3b97a8a2a54d4d0571911691677ae9046413103"
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False

m=r["scheduler_policy"]["adaptive_meta_scheduler"]
assert m["policy_git_blob_sha"]=="10aa59870c12b330ca72a2b3e6eac3c41386b2af"
assert m["final_activation_git_blob_sha"]=="572ba5c0be970de4e4ea96b64d94746d002cae51"
assert m["verification_git_blob_sha"]=="dc14c99706257f42d2af7837fb439b330fa9f708"
assert m["execution_authority"] is False
assert m["promotion_authority"] is False
assert m["fresh_reality_authority"] is False

assert "relative_elo_absolute_proof_nontransport" in r["scheduler_policy"]
assert "synthesis_dimension_scorers_and_strict_reducer" in r["scheduler_policy"]

p=r["current_residual_root_partition"]
assert (p["root1_positive_gap_count"],p["root2_only_count"],p["root3_only_count"],p["root2_and_root3_count"])==(0,16,7,3)

print("PASS final V12/V4 projection")
print("PASS terminal truth unchanged; scheduling reductions active; no fresh-reality authority")
