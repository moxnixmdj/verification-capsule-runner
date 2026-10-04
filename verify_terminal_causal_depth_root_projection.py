from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_causal_depth_root_projection_20261004_sol"
EXPECTED={
 "ROOT.json":"f610d7dee1962db6a0530cb0af4a8ad5834398dc",
 "ACTIVATION.json":"9c5e22200edb8f6afe853e9bccb447e7c25d845f",
 "VERIFICATION.json":"f9423a72ced49ecc2d2928a7c41239994a3a323c",
}
def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

root=json.loads((SUB/"ROOT.json").read_text())
act=json.loads((SUB/"ACTIVATION.json").read_text())
ver=json.loads((SUB/"VERIFICATION.json").read_text())

assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False,
}
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json"
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False

ptr=root["scheduler_policy"]["terminal_causal_depth_collapse"]
assert ptr["activation_path"]=="canonical/governance/TERMINAL_CAUSAL_DEPTH_COLLAPSE_ACTIVATION_V1.json"
assert ptr["activation_git_blob_sha"]==EXPECTED["ACTIVATION.json"]
assert ptr["verification_path"]=="canonical/verification/TERMINAL_CAUSAL_DEPTH_COLLAPSE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
assert ptr["verification_git_blob_sha"]==EXPECTED["VERIFICATION.json"]
assert ptr["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__SCHEDULING_ONLY__ZERO_CREDIT"
assert ptr["execution_authority"] is False
assert ptr["promotion_authority"] is False
assert ptr["fresh_reality_authority"] is False
assert ptr["acceptance_credit_delta"]==0

assert act["status"]=="ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__SCHEDULING_ONLY__ZERO_CREDIT"
assert act["authority"]=={"scheduling":True,"meta_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in act["accounting"].values())
assert "FRESH_REALITY_BLOCK" in act["preserved"]
assert "26_UNRESOLVED_ATOMIC_PREDICATES" in act["preserved"]

assert ver["independent_runner"]["verifier_merge_commit"]=="4445e8d4ca10983b4c074fca2c6d96e4d847cd28"
assert ver["independent_runner"]["workflow_run_id"]==37179570440
assert ver["independent_runner"]["workflow_job_id"]==111369199787
assert ver["independent_runner"]["conclusion"]=="success"
assert all(v==0 for v in ver["accounting"].values())
assert "NO_FRESH_REALITY_AUTHORITY" in ver["hard_nonclaims"]
assert "NO_EXECUTION_OR_PROMOTION_AUTHORITY" in ver["hard_nonclaims"]

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
 "policy_verification_blob":EXPECTED["VERIFICATION.json"],
 "terminal":False,
 "accepted_families":5,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "root2_effective_frontier":"V11",
 "execution_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
