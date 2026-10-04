import json
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text())

act=load("verification_inputs/root2_external_source_activation_v1.json")
v8=load("verification_inputs/root2_active_v8_parent.json")
rec=load("verification_inputs/root2_external_source_receipt_v1.json")

assert act["schema"]=="PROJECT_BRAIN_ROOT2_EXTERNAL_PRIMARY_SOURCE_REFRESH_ACTIVATION_V1"
assert v8["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8"
assert rec["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert act["active_parent"]["git_blob_sha"]=="2eaeb74fe306ee2507145e26eb731f69f46e6153"
assert act["source_refresh"]["git_blob_sha"]=="85f2a5de5885d158e08db6cceebf0e30cf5d5bb0"
assert act["verification"]["git_blob_sha"]=="a0f46fe3b577c91686b1b8cc5b2436b35556a708"
assert act["verification"]["workflow_run_id"]==37172799883
assert act["verification"]["workflow_job_id"]==111349049144
assert act["verification"]["conclusion"]=="success"
assert act["accounting"]==v8["accounting"]==rec["accounting"]
assert act["compatibility"]=={
    "v9_candidate_unchanged": True,
    "root1_unchanged": True,
    "root3_unchanged": True,
    "acceptance_unchanged": True
}
assert len(act["delete"])==6
assert set(act["delete"])==set(rec["scheduler_deletions_verified"])
assert act["execution_authority"] is False
assert act["promotion_authority"] is False
assert act["fresh_reality_authority"] is False
assert act["independent_projection_verification_required"] is True
print("ROOT2_EXTERNAL_SOURCE_ACTIVATION_V1: PASS")
