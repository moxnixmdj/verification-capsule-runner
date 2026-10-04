#!/usr/bin/env python3
import json
from pathlib import Path

R=Path(__file__).resolve().parent

def J(name):
    return json.loads((R/name).read_text())

act=J("ROOT2_FRONTIER_V10_ACTIVATION_V1.json")
root=J("TERMINAL_ROOT_CAUSE_STATE_V1.json")
bridge=J("ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
term=J("CURRENT_TERMINAL_AUTHORITY_V1.json")

assert act["schema"]=="PROJECT_BRAIN_ROOT2_FRONTIER_V10_ACTIVATION_V1"
assert act["authority"]=={
    "scheduling": True,
    "effective_scheduling": True,
    "execution": False,
    "promotion": False,
    "fresh_reality": False,
}
assert "SATISFIED" in act["activation_condition"]
assert act["pointer_projection_verification"]["conclusion"]=="success"

ac=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ac["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert ac["effective_scheduling_authority"] is True
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert root["current_acceptance"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
    "total_families":19,"total_atomic":38,"terminal":False
}

bc=bridge["root2_closure_controller_v2"]
assert bc["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert bc["effective_scheduling_authority"] is True
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False

ts=term["sources"]["root2_closure_v2_current_frontier"]
assert ts["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json"
assert ts["effective_scheduling_authority"] is True
assert ts["pointer_projection_verification"].endswith("ROOT2_V10_POINTER_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
assert term["truth"]["achieved"] is False

frontier_sha="2012926814d0d06405da56da64e589b06fef1756"
assert act["frontier_git_blob_sha"]==frontier_sha
assert ac["current_frontier_git_blob_sha"]==frontier_sha
assert bc["frontier_git_blob_sha"]==frontier_sha
assert ts["git_blob_sha"]==frontier_sha

activation_sha="d0c551edcce3ca5037c72380e94f498ae8b42660"
assert ac["current_frontier_activation_git_blob_sha"]==activation_sha
assert bc["frontier_activation_git_blob_sha"]==activation_sha
assert ts["activation_git_blob_sha"]==activation_sha

for obj in (act,):
    a=obj["accounting"]
    assert a["incremental_spend_usd"]==0
    assert a["new_reality_units_consumed"]==0
    assert a["terminal_cases_consumed"]==0
    assert a["acceptance_credit_delta"]==0
    assert a["family_credit_delta"]==0
    assert a["capability_credit_delta"]==0
    assert a["ownership_credit_delta"]==0

print(json.dumps({
 "status":"PASS",
 "frontier":"V10",
 "effective_scheduling":True,
 "execution":False,
 "promotion":False,
 "fresh_reality":False,
 "acceptance":"5/19",
 "atomic":"12/38"
},sort_keys=True))
