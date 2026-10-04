import json, pathlib, subprocess

FILES={
 "frontier":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json",
 "activation":"subject/ROOT2_FRONTIER_V8_ACTIVATION_V1.json",
 "terminal":"subject/CURRENT_TERMINAL_AUTHORITY_V1.json",
 "root":"subject/TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "bridge":"subject/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
}
EXPECTED={
 "frontier":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
 "activation":"0ab521eae842f65bcf17b62ec15f40bdc00ccfcb",
 "terminal":"bde3371358fed309967513a7d37718d280bb8dcc",
 "root":"34576332a8b8b9d1d813bf13025789a0de8909a7",
 "bridge":"f289381c2ff132af336c7472feb7e1e41dc9e1a4",
}
def blob(p): return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])

f=json.loads(pathlib.Path(FILES["frontier"]).read_text())
a=json.loads(pathlib.Path(FILES["activation"]).read_text())
t=json.loads(pathlib.Path(FILES["terminal"]).read_text())
r=json.loads(pathlib.Path(FILES["root"]).read_text())
b=json.loads(pathlib.Path(FILES["bridge"]).read_text())

assert f["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8"
assert f["exact_state"]["accepted_families"]==5
assert f["exact_state"]["open_families"]==14
assert f["exact_state"]["proved_atomic"]==12
assert f["exact_state"]["unresolved_atomic"]==26
assert f["accounting"]["incremental_spend_usd"]==0
assert f["accounting"]["terminal_cases_consumed"]==0
assert f["execution_authority"] is False
assert f["promotion_authority"] is False
assert f["fresh_reality_authority"] is False

assert a["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert a["verification_git_blob_sha"]=="7e2d71144853c41fadab55f4074d484edf46e651"
assert a["authority"]["effective_scheduling"] is False
assert a["authority"]["execution"] is False
assert a["authority"]["promotion"] is False
assert a["authority"]["fresh_reality"] is False

tp=t["sources"]["root2_closure_v2_current_frontier"]
assert tp["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert tp["git_blob_sha"]==EXPECTED["frontier"]
assert tp["verification_git_blob_sha"]=="7e2d71144853c41fadab55f4074d484edf46e651"
assert tp["activation_git_blob_sha"]==EXPECTED["activation"]
assert tp["effective_scheduling_authority"] is False

rp=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert rp["current_frontier_git_blob_sha"]==EXPECTED["frontier"]
assert rp["current_frontier_verification_git_blob_sha"]=="7e2d71144853c41fadab55f4074d484edf46e651"
assert rp["current_frontier_activation_git_blob_sha"]==EXPECTED["activation"]
assert rp["effective_scheduling_authority"] is False
assert r["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert r["scheduler_policy"]["root2_effective_scheduling_authority"] is False

bp=b["root2_closure_controller_v2"]
assert bp["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert bp["frontier_verification_git_blob_sha"]=="7e2d71144853c41fadab55f4074d484edf46e651"
assert bp["frontier_activation_git_blob_sha"]==EXPECTED["activation"]
assert bp["effective_scheduling_authority"] is False

print("ROOT2_V8_POINTER_PROJECTION_PASS__COHERENT__EFFECTIVE_SCHEDULING_FALSE__ZERO_CREDIT")
