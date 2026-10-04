import json, pathlib, subprocess

FILES = {
  "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json",
  "terminal": "subject/CURRENT_TERMINAL_AUTHORITY_V1.json",
  "root": "subject/TERMINAL_ROOT_CAUSE_STATE_V1.json",
  "bridge": "subject/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
}
EXPECTED = {
  "frontier": "fcbdb818b63b4986b026db29c400a47373a26fdb",
  "terminal": "7d678a199558b846822ff44535bc0efe41919e51",
  "root": "2e2317b3e50ef5a8bffb24332e265950dc25a1ce",
  "bridge": "0af18806dbbff2754e396dd47cf88fc504f9a963",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

for key,path in FILES.items():
    got=blob(path)
    assert got==EXPECTED[key], (key,got,EXPECTED[key])

f=json.loads(pathlib.Path(FILES["frontier"]).read_text())
t=json.loads(pathlib.Path(FILES["terminal"]).read_text())
r=json.loads(pathlib.Path(FILES["root"]).read_text())
b=json.loads(pathlib.Path(FILES["bridge"]).read_text())

assert f["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6"
assert f["exact_state"]["accepted_families"]==5
assert f["exact_state"]["open_families"]==14
assert f["exact_state"]["proved_atomic"]==12
assert f["exact_state"]["unresolved_atomic"]==26
assert f["accounting"]["incremental_spend_usd"]==0
assert f["accounting"]["terminal_cases_consumed"]==0
assert f["fresh_reality_authority"] is False
assert f["execution_authority"] is False
assert f["promotion_authority"] is False

x=t["sources"]["root2_closure_v2_current_frontier"]
assert x["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert x["git_blob_sha"]==EXPECTED["frontier"]
assert x["effective_scheduling_authority"] is False

c=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert c["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert c["current_frontier_git_blob_sha"]==EXPECTED["frontier"]
assert c["effective_scheduling_authority"] is False
assert r["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert r["scheduler_policy"]["root2_effective_scheduling_authority"] is False

m=b["root2_closure_controller_v2"]
assert m["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert m["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert m["effective_scheduling_authority"] is False
assert b["execution_authority"] is False
assert b["promotion_authority"] is False
assert b["fresh_reality_authority"] is False

print("ROOT2_V6_PROJECTION_INDEPENDENT_PASS__POINTER_COHERENT__EFFECTIVE_SCHEDULING_FALSE__ZERO_CREDIT")

# trigger independent base-resident workflow
