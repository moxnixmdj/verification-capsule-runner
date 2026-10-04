#!/usr/bin/env python3
import json, pathlib, subprocess

BASE=pathlib.Path("subject/relative_elo_root_projection_20261004_sol")
FILES={
  "root":BASE/"ROOT_STATE.json",
  "activation":BASE/"ACTIVATION.json",
  "verification":BASE/"VERIFICATION.json",
}
EXPECTED={
  "root":"0e56e97fafbb9199c2bc6b700c76c2fb3c40ebca",
  "activation":"5edaf436becf45c8d8f3477ac7a53a1e8ac3a63a",
  "verification":"b6daf8b1892a8dc11020b6c5a4102b1fed256240",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

root=json.loads(FILES["root"].read_text())
act=json.loads(FILES["activation"].read_text())
ver=json.loads(FILES["verification"].read_text())

assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
res=root["current_residual_root_partition"]
assert (res["root1_positive_gap_count"],res["root2_only_count"],res["root3_only_count"],res["root2_and_root3_count"])==(0,16,7,3)

ptr=root["scheduler_policy"]["relative_elo_absolute_proof_nontransport"]
assert ptr["activation_git_blob_sha"]==EXPECTED["activation"]
assert ptr["verification_git_blob_sha"]==EXPECTED["verification"]
assert ptr["affected_predicate_count"]==3
assert set(ptr["affected_predicates"])=={
 "PROWORK_GDPVAL_GE_1846",
 "PROWORK_AA_BRIEFCASE_GE_1822",
 "ARTIFACT_AA_BRIEFCASE_GE_1822",
}
assert ptr["execution_authority"] is False
assert ptr["promotion_authority"] is False
assert ptr["fresh_reality_authority"] is False

assert act["authority"]=={"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert act["scheduler_effect"]["effect_kind"]=="SEARCH_SPACE_PRUNING_ONLY"
assert "MATCHED_EMPIRICAL_COMPARISON" in act["scheduler_effect"]["preserve"]
assert "OWNER_RESULT" in act["scheduler_effect"]["preserve"]
assert "RELATIVE_SCORE_BRIDGE_STRONGER_PROOF" in act["scheduler_effect"]["preserve"]

assert ver["independent_runner"]["conclusion"]=="success"
assert ver["independent_runner"]["workflow_run_id"]==37178103901
assert ver["independent_runner"]["workflow_job_id"]==111364873958
assert len(ver["affected_predicates"])==3

assert root["accounting"]=={
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,
 "new_reality_units_consumed":0,"incremental_spend_usd":0
}
print("PASS: relative Elo route-pruning root projection is exact")
print("PASS: terminal truth unchanged at 5/19, 12/38, 26 unresolved")
print("PASS: owner, comparator and matched routes preserved")
print("PASS: zero credit and no execution/promotion/fresh-reality authority")
