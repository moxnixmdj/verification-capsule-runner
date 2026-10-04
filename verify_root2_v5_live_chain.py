import json, pathlib, subprocess
FILES={
"root":"subject/LIVE_TERMINAL_ROOT_CAUSE_STATE_V1.json",
"activation":"subject/ROOT2_V5_ACTIVATION_V1.json",
"v5":"subject/ROOT2_V5_FRONTIER.json",
"verification":"subject/ROOT2_V5_PROJECTION_VERIFICATION.json",
}
EXPECTED={
"root":"1d26f794f32b14c4d0f6aa6fcef42337dda8a47e",
"activation":"2d15df0daab51c5cc61c4194197da7f7fcd5a1b0",
"v5":"e948022f0a4e8d91b949a5155d850d56aa137c87",
"verification":"2475a8583e2ed2889c3e9e0613ae3bcf269ffc82",
}
def blob(p): return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items(): assert blob(p)==EXPECTED[k], (k,blob(p),EXPECTED[k])
root=json.loads(pathlib.Path(FILES["root"]).read_text())
act=json.loads(pathlib.Path(FILES["activation"]).read_text())
v5=json.loads(pathlib.Path(FILES["v5"]).read_text())
ver=json.loads(pathlib.Path(FILES["verification"]).read_text())
assert root["current_acceptance"]=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
assert r2["current_frontier_git_blob_sha"]==EXPECTED["v5"]
assert r2["current_frontier_activation_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5_ACTIVATION_V1.json"
assert r2["current_frontier_activation_git_blob_sha"]==EXPECTED["activation"]
assert r2["current_frontier_verification_path"]=="canonical/verification/ROOT2_V5_PROJECTION_VERIFICATION_20261004_V1.json"
assert r2["current_frontier_verification_git_blob_sha"]==EXPECTED["verification"]
assert root["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
assert root["scheduler_policy"]["fresh_reality_before_zero_reality_fixed_point"] is False
assert act["subject"]["git_blob_sha"]==EXPECTED["v5"]
assert act["verification"]["git_blob_sha"]==EXPECTED["verification"]
assert act["authority"]=={"scheduling_authority":True,"effective_scheduling_authority":True,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
assert ver["verifier"]["conclusion"]=="success"
assert ver["verified"]["accepted_families"]==5 and ver["verified"]["proved_atomic"]==12 and ver["verified"]["unresolved_atomic"]==26
assert ver["verified"]["circleci_free_xlarge_deleted"] is True
assert ver["verified"]["finance_agent_v2_public_runner_bound"] is True
assert v5["tb4_carrier_portfolio"]["candidates"][0]["provider"]=="Buildkite"
assert [x["provider"] for x in v5["tb4_carrier_portfolio"]["deleted"]]==["CircleCI"]
assert v5["execution_authority"] is False and v5["promotion_authority"] is False and v5["fresh_reality_authority"] is False
print("PASS: live Root2 V5 authority chain is exact and fail-closed")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved; no fresh reality")
