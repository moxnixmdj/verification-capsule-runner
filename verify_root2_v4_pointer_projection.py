import json, pathlib, subprocess

T="subject/CURRENT_TERMINAL_AUTHORITY_V1.json"
M="subject/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json"
R="subject/TERMINAL_ROOT_CAUSE_STATE_V1.json"

EXPECTED={
 T:"1f308cf9dd1b684cc260fd9a65f60ee86b612271",
 M:"71c8de45974681e5fb8c36a7b7cbe6a5a85075e8",
 R:"bb335e174c3595e9acd760cda4f79dda6d61a59a",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

for p,sha in EXPECTED.items():
    assert blob(p)==sha,(p,blob(p),sha)

t=json.loads(pathlib.Path(T).read_text())
m=json.loads(pathlib.Path(M).read_text())
r=json.loads(pathlib.Path(R).read_text())

frontier="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json"
frontier_sha="8c90a1dc4903f9b895788ff2864822d6ebc26ac9"
activation="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4_ACTIVATION_V1.json"
activation_sha="53a34935ae664e89f53caf486366f7f3484ed0f4"
verification="canonical/verification/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
verification_sha="d3e116d3613b0666648733491449f13a8127a543"

x=t["sources"]["root2_closure_v2_current_frontier"]
assert x["path"]==frontier and x["git_blob_sha"]==frontier_sha
assert x["activation"]==activation and x["activation_git_blob_sha"]==activation_sha
assert x["verification"]==verification and x["verification_git_blob_sha"]==verification_sha
assert "POINTER_PROJECTION_REVERIFY_PENDING" in x["status"]
assert t["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert t["truth"]["achieved"] is False

y=m["root2_closure_controller_v2"]
assert y["frontier_path"]==frontier and y["frontier_git_blob_sha"]==frontier_sha
assert y["frontier_activation_path"]==activation and y["frontier_activation_git_blob_sha"]==activation_sha
assert y["frontier_verification_path"]==verification and y["frontier_verification_git_blob_sha"]==verification_sha
assert m["fresh_reality_authority"] is False
assert m["execution_authority"] is False
assert m["incremental_spend_usd"]==0
assert m["terminal_cases_consumed"]==0

z=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert z["current_frontier_path"]==frontier and z["current_frontier_git_blob_sha"]==frontier_sha
assert z["current_frontier_activation_path"]==activation and z["current_frontier_activation_git_blob_sha"]==activation_sha
assert z["current_frontier_verification_path"]==verification and z["current_frontier_verification_git_blob_sha"]==verification_sha
assert r["scheduler_policy"]["root2_current_frontier"]==frontier
assert r["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False
}
p=r["current_residual_root_partition"]
assert p["root1_positive_gap_count"]==0
assert p["root2_only_count"]==16
assert p["root3_only_count"]==7
assert p["root2_and_root3_count"]==3
assert r["accounting"]["incremental_spend_usd"]==0
assert r["accounting"]["acceptance_credit_delta"]==0

print("ROOT2_V4_POINTER_PROJECTION_PASS__COUNTS_UNCHANGED__NO_FRESH_REALITY")
