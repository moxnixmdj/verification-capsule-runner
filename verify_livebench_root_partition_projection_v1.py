#!/usr/bin/env python3
import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
p=json.loads((ROOT/"subject/livebench_local_root1_20261004/projection.json").read_text())
c=json.loads((ROOT/"subject/livebench_local_root1_20261004/candidate.json").read_text())
assert p["schema"]=="PROJECT_BRAIN_LIVEBENCH_ROOT_PARTITION_PROJECTION_V1"
assert p["source_reclassification"]["git_blob_sha"]=="eef18a73b23db53082b934976bcbd05cab9c5684"
assert p["independent_classification"]["workflow_run_id"]==37196376134
assert p["independent_classification"]["workflow_job_id"]==111419008329
assert p["independent_classification"]["conclusion"]=="success"
b=p["before"]; a=p["after"]
assert b["unresolved_total"]==26 and a["unresolved_total"]==26
assert b["root1_only_count"]==0 and a["root1_only_count"]==1
assert b["root2_only_count"]==16 and a["root2_only_count"]==15
assert b["root3_only_count"]==a["root3_only_count"]==7
assert b["root2_and_root3_count"]==a["root2_and_root3_count"]==3
assert "LIVEBENCH_IF_GE_65_7" in b["root2_only"]
assert "LIVEBENCH_IF_GE_65_7" not in a["root2_only"]
assert a["root1_only"]==["LIVEBENCH_IF_GE_65_7"]
assert b["root3_only"]==a["root3_only"]
assert b["root2_and_root3"]==a["root2_and_root3"]
assert a["root1_positive_gap_count"]==1
assert 1+15+7+3==26==p["invariants"]["partition_sum_after"]
assert c["root_transition"]["root1_positive_gap"] is True
assert c["root_transition"]["root2_local_residual"] is False
assert p["execution_authority"] is False and p["promotion_authority"] is False and p["fresh_reality_authority"] is False
for k,v in p["accounting"].items():
    assert v==0
print("PASS:LIVEBENCH_ROOT_PARTITION_PROJECTION_V1")
