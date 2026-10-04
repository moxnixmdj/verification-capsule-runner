#!/usr/bin/env python3
import json
from pathlib import Path

p=Path("livebench_if_exact200_acceptance_reduction_candidate_v1.json")
x=json.loads(p.read_text())
assert x["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_EXACT200_ACCEPTANCE_REDUCTION_CANDIDATE_V1"
assert x["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert x["target_family"]=="INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT"
r=x["exact_result"]
assert r["brain_percent"] >= r["stricter_public_opus_equal_task_mean_floor_percent"]
assert r["stricter_public_opus_equal_task_mean_floor_percent"] >= r["frozen_registry_threshold_percent"]
assert r["predicate_forced"]=="PASS"
e=x["independent_exact_execution"]
assert e["workflow_run_id"]==37238837049
assert e["workflow_job_id"]==111543251329
assert e["conclusion"]=="success"
assert e["exact_brain_git_blob_gate"] is True
assert e["exact_brain_bytes_execution_pass"] is True
assert e["receipt_persist_pass"] is True
assert e["receipt_git_blob_sha"]=="165192ffa20e052f094371c04d15da6c9147a146"
b=x["intended_atomic_reduction"]["before"]
a=x["intended_atomic_reduction"]["after"]
assert (b["accepted_families"],a["accepted_families"])==(5,5)
assert (b["open_families"],a["open_families"])==(14,14)
assert a["proved_atomic"]==b["proved_atomic"]+1==13
assert a["unresolved_atomic"]==b["unresolved_atomic"]-1==25
assert a["root2_only"]==b["root2_only"]-1==15
assert a["root3_only"]==b["root3_only"]==7
assert a["root2_and_root3"]==b["root2_and_root3"]==3
assert a["root2_touching"]==b["root2_touching"]-1==18
assert a["root2_only"]+a["root3_only"]+a["root2_and_root3"]==a["unresolved_atomic"]
assert a["root2_only"]+a["root2_and_root3"]==a["root2_touching"]
g=x["family_guard"]
assert g["family_remains_open"] is True
assert set(g["remaining_family_predicates"])=={"IF_SCOPE_BOUNDARY_NONINFERIOR","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"}
assert x["accounting"]["family_credit_delta"]==0
assert x["accounting"]["terminal_goal_credit_delta"]==0
assert x["promotion_authority"] is False
print(json.dumps({
 "status":"PASS",
 "target_predicate":x["target_predicate"],
 "brain_percent":r["brain_percent"],
 "threshold_percent":r["frozen_registry_threshold_percent"],
 "proved_atomic_after":a["proved_atomic"],
 "unresolved_atomic_after":a["unresolved_atomic"],
 "root2_touching_after":a["root2_touching"],
 "family_remains_open":g["family_remains_open"]
},sort_keys=True))
