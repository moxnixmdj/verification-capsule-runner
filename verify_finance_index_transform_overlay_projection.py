import json, pathlib, subprocess

FILES={
  "cut":"subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_20261004_V1.json",
  "receipt":"subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
  "activation":"subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_ACTIVATION_V1.json",
  "terminal":"subject/CURRENT_TERMINAL_AUTHORITY_V1.json",
  "root":"subject/TERMINAL_ROOT_CAUSE_STATE_V1.json",
  "bridge":"subject/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
}
EXPECTED={
  "cut":"2a831b8632b18fe9e10ed423f131b6ae93d99b77",
  "receipt":"8aea6757479980c9f2e2538a4f2651ad23653c10",
  "activation":"d286b55e361194a77acd21def918d12e07227964",
  "terminal":"5f09fe733cd97761a984da7b7614f0ca237b0aba",
  "root":"285e2c35d71cb95706b9bdbb3b67942998709fe8",
  "bridge":"583efdcd4290a49176304a23e8a4ff9af945f50d",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

cut=json.loads(pathlib.Path(FILES["cut"]).read_text())
receipt=json.loads(pathlib.Path(FILES["receipt"]).read_text())
act=json.loads(pathlib.Path(FILES["activation"]).read_text())
term=json.loads(pathlib.Path(FILES["terminal"]).read_text())
root=json.loads(pathlib.Path(FILES["root"]).read_text())
bridge=json.loads(pathlib.Path(FILES["bridge"]).read_text())

assert receipt["subject"]["git_blob_sha"]==EXPECTED["cut"]
assert receipt["verifier"]["workflow_run_id"]==37174229191
assert receipt["verifier"]["workflow_job_id"]==111353390105
assert receipt["verifier"]["conclusion"]=="success"

assert act["subject"]["git_blob_sha"]==EXPECTED["cut"]
assert act["verification"]["git_blob_sha"]==EXPECTED["receipt"]
assert act["authority"]["scheduling_authority"] is True
assert act["authority"]["effective_scheduling_authority"] is False
assert act["authority"]["execution_authority"] is False
assert act["authority"]["promotion_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False

for overlay in [
    term["sources"]["finance_index_public_transform_saturation"],
    root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["finance_index_public_transform_saturation"],
    bridge["root2_closure_controller_v2"]["finance_index_public_transform_saturation"],
]:
    assert overlay["subject_git_blob_sha"]==EXPECTED["cut"]
    assert overlay["verification_git_blob_sha"]==EXPECTED["receipt"]
    assert overlay["activation_git_blob_sha"]==EXPECTED["activation"]
    assert overlay["effective_scheduling_authority"] is False

assert root["scheduler_policy"]["finance_index_public_transform_saturation_effective"] is False
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["open_families"]==14
assert root["current_acceptance"]["proved_atomic"]==12
assert root["current_acceptance"]["unresolved_atomic"]==26
assert root["current_acceptance"]["terminal"] is False
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False

print("FINANCE_INDEX_TRANSFORM_OVERLAY_PROJECTION_PASS__NON_EFFECTIVE__ZERO_CREDIT")
