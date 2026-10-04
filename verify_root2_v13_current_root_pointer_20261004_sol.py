from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"root2_v13_current_root_pointer_20261004_sol"
EXPECTED={
 "CANDIDATE_ROOT.json":"e1410880f63d92de1b4787fd6ce2c0535b6cdd19",
 "PRIOR_ROOT.json":"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59",
 "V13.json":"bb631b80eea5a183728fb27e2aff99bbe63f1757",
 "V13_ACTIVATION.json":"08c84d8f0a46ff0f13943388306195fea79ca6d7",
 "V13_VERIFICATION.json":"dd810106cf30f101453da07e2ef37cb81d7faddd",
}

def blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for name,expected in EXPECTED.items():
    got=blob_sha(SUB/name)
    assert got==expected,(name,got,expected)

cand=json.loads((SUB/"CANDIDATE_ROOT.json").read_text())
prior=json.loads((SUB/"PRIOR_ROOT.json").read_text())
v13=json.loads((SUB/"V13.json").read_text())
act=json.loads((SUB/"V13_ACTIVATION.json").read_text())
ver=json.loads((SUB/"V13_VERIFICATION.json").read_text())

assert cand["current_acceptance"]==prior["current_acceptance"]
assert cand["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
assert cand["current_residual_root_partition"]==prior["current_residual_root_partition"]
assert cand["root3_current_execution_state"]==prior["root3_current_execution_state"]
assert cand["accounting"]==prior["accounting"]
assert all(v==0 for v in cand["accounting"].values())

cc=cand["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
pc=prior["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert pc["current_frontier_path"].endswith("V12.json")
assert cc["current_frontier_path"].endswith("V13.json")
assert cc["current_frontier_git_blob_sha"]==EXPECTED["V13.json"]
assert cc["current_frontier_verification_git_blob_sha"]==EXPECTED["V13_VERIFICATION.json"]
assert cc["current_frontier_activation_git_blob_sha"]==EXPECTED["V13_ACTIVATION.json"]
assert "ACTIVE_IFF_CANONICAL_VERIFICATION_RECEIPT_EXISTS" in cc["status"]
assert cc["fresh_reality_authority"] is False

sp=cand["scheduler_policy"]
assert sp["root2_current_frontier"].endswith("V13.json")
assert sp["root2_effective_scheduling_authority"] is True
proj=sp["root2_v13_projection"]
assert proj["frontier_git_blob_sha"]==EXPECTED["V13.json"]
assert proj["verification_git_blob_sha"]==EXPECTED["V13_VERIFICATION.json"]
assert proj["activation_git_blob_sha"]==EXPECTED["V13_ACTIVATION.json"]
assert proj["required_projection_verification_path"]=="canonical/verification/ROOT2_V13_CURRENT_ROOT_POINTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
assert proj["required_subject_root_blob"]=="SELF"
assert proj["execution_authority"] is False
assert proj["promotion_authority"] is False
assert proj["fresh_reality_authority"] is False

lb=sp["livebench_if_thin_adapter_completion"]
assert lb["status"]=="ACTIVE__8_OF_8_THIN_ADAPTER_FIELDS_COMPLETE__ZERO_CREDIT"
assert len(lb["remaining_zero_reality"])==3
assert lb["separate_fresh_reality_authority_required"] is True
assert lb["score_still_open"] is True

meta=sp["adaptive_meta_scheduler"]
assert "SUPERSEDED_FOR_ROOT2_SPECIFIC_SCHEDULING_BY_V13" in meta["status"]
assert meta["execution_authority"] is False
assert meta["promotion_authority"] is False
assert meta["fresh_reality_authority"] is False

assert v13["exact_state"]["accepted_families"]==5
assert v13["exact_state"]["proved_atomic"]==12
assert v13["exact_state"]["unresolved_atomic"]==26
assert v13["exact_state"]["root2_touching_predicates"]==19
assert ver["verifier"]["conclusion"]=="success"
assert ver["verified"]["livebench_thin_adapter_8_of_8_complete"] is True
assert ver["verified"]["fresh_reality_block_unchanged"] is True
assert act["authority"]=={"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(x==0 for x in act["accounting"].values())

print(json.dumps({
 "status":"PASS",
 "candidate_root_blob":EXPECTED["CANDIDATE_ROOT.json"],
 "root2_frontier":"V13",
 "terminal_counts":"5_OF_19__12_OF_38__26_UNRESOLVED",
 "root3_unchanged":True,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0
},sort_keys=True))
