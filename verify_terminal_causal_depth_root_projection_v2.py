from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_causal_depth_root_projection_v2_20261004_sol"
EXPECTED={
 "ROOT.json":"5e03218edf72b031e6bbafd6a2ee010cc2c0acd9",
 "ACTIVATION.json":"1c4400af63533e236847189b17b11e8dd7f80107",
 "POLICY_VERIFICATION.json":"bf6e682b8c55eab3bfafe424c830657c6ffdbcd9",
}
def git_blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

root=json.loads((SUB/"ROOT.json").read_text())
act=json.loads((SUB/"ACTIVATION.json").read_text())
pv=json.loads((SUB/"POLICY_VERIFICATION.json").read_text())

assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False,
}
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12.json"
assert r2["status"]=="ACTIVE__ROOT2_FRONTIER_V12_INDEPENDENT_PASS__CURRENT_MAIN_POINTER_PROJECTION_ACTIVE__ZERO_CREDIT"
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False

ptr=root["scheduler_policy"]["terminal_causal_depth_collapse"]
assert ptr["activation_git_blob_sha"]==EXPECTED["ACTIVATION.json"]
assert ptr["policy_verification_git_blob_sha"]==EXPECTED["POLICY_VERIFICATION.json"]
assert ptr["projection_verification_path"]=="canonical/verification/TERMINAL_CAUSAL_DEPTH_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V2.json"
assert ptr["status"]=="ACTIVE_IFF_EXACT_ROOT_PROJECTION_RECEIPT_EXISTS_AND_PASSES__SCHEDULING_ONLY__ZERO_CREDIT"
assert ptr["authority_source"].startswith("READ_EFFECTIVE_ROOT2_FRONTIER")
assert ptr["execution_authority"] is False
assert ptr["promotion_authority"] is False
assert ptr["fresh_reality_authority"] is False
assert ptr["acceptance_credit_delta"]==0
assert ptr["family_credit_delta"]==0
assert ptr["capability_credit_delta"]==0
assert ptr["ownership_credit_delta"]==0

assert act["status"]=="ACTIVATION_CONTRACT__ACTIVE_ONLY_WITH_CURRENT_INDEPENDENT_POLICY_RECEIPT_AND_ROOT_PROJECTION_PASS__ZERO_CREDIT"
assert act["verification_contract"]["required_policy_verification_path"]=="canonical/verification/TERMINAL_CAUSAL_DEPTH_COLLAPSE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
assert act["authority"]=={"scheduling":True,"meta_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in act["accounting"].values())

assert pv["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__DYNAMIC_ROOT2_AUTHORITY__EXACT_CANDIDATE_BYTES__ZERO_CREDIT"
assert pv["subject"]["policy"]["git_blob_sha"]=="ed50678f56dc873eda5aada1c5509286d216ab94"
assert pv["subject"]["activation_contract"]["git_blob_sha"]==EXPECTED["ACTIVATION.json"]
assert pv["independent_runner"]["pull_request"]==1698
assert pv["independent_runner"]["verifier_merge_commit"]=="ede6819c526deae202b3c3ad6f25de18cb26c0cb"
assert pv["independent_runner"]["workflow_run_id"]==37179907460
assert pv["independent_runner"]["workflow_job_id"]==111370192934
assert pv["independent_runner"]["conclusion"]=="success"
assert all(v==0 for v in pv["accounting"].values())

partition=root["current_residual_root_partition"]
assert partition["unresolved_total"]==26
assert partition["root1_positive_gap_count"]==0
assert partition["root2_only_count"]==16
assert partition["root3_only_count"]==7
assert partition["root2_and_root3_count"]==3

print(json.dumps({
 "status":"PASS",
 "exact_root_blob":EXPECTED["ROOT.json"],
 "activation_blob":EXPECTED["ACTIVATION.json"],
 "policy_verification_blob":EXPECTED["POLICY_VERIFICATION.json"],
 "root2_effective_frontier":"V12",
 "accepted_families":5,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "terminal":False,
 "execution_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
