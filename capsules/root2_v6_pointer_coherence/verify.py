#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

BASE=Path(__file__).parent
FILES={
  "frontier":("frontier.json","fcbdb818b63b4986b026db29c400a47373a26fdb"),
  "projection":("projection_verification.json","e2756cec5781d77f1335b01ac896cc77d44fa654"),
  "activation":("activation.json","c0eb1e78bd9b39fbb3e188fbf68b3b0d4053b5f9"),
  "terminal":("terminal_authority.json","118925dd52f5551baced2fde466748de67a173a7"),
  "root":("root_state.json","f769f5731e64d376d77c18bbda2f40c69c9ab9d7"),
  "bridge":("measurement_bridge.json","6b9ec434d11d9159a4aee0ec150258ab10b6d83a"),
}
def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
J={}
for k,(name,sha) in FILES.items():
    b=(BASE/name).read_bytes()
    assert git_blob(b)==sha,(k,git_blob(b),sha)
    J[k]=json.loads(b)

F=J["frontier"]; P=J["projection"]; A=J["activation"]; T=J["terminal"]; R=J["root"]; B=J["bridge"]
assert F["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6"
s=F["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert (s["root2_only_count"],s["root3_only_count"],s["root2_and_root3_count"],s["root2_touching_predicates"])==(16,7,3,19)
assert F["execution_authority"] is False and F["promotion_authority"] is False and F["fresh_reality_authority"] is False
assert F["accounting"]["incremental_spend_usd"]==0 and F["accounting"]["terminal_cases_consumed"]==0
assert F["accounting"]["acceptance_credit_delta"]==0

assert P["subject"]["git_blob_sha"]==FILES["frontier"][1]
assert P["verifier"]["pull_request"]==1604
assert P["verifier"]["workflow_run_id"]==37170190995
assert P["verifier"]["workflow_job_id"]==111341422899
assert P["verifier"]["conclusion"]=="success"
assert P["verified"]["accepted_families"]==5 and P["verified"]["proved_atomic"]==12 and P["verified"]["unresolved_atomic"]==26
assert P["execution_authority"] is False and P["promotion_authority"] is False and P["fresh_reality_authority"] is False

assert A["subject"]["git_blob_sha"]==FILES["frontier"][1]
assert A["verification"]["git_blob_sha"]==FILES["projection"][1]
assert A["authority"]["scheduling_authority"] is True
assert A["authority"]["effective_scheduling_authority"] is True
assert A["authority"]["execution_authority"] is False
assert A["authority"]["promotion_authority"] is False
assert A["authority"]["fresh_reality_authority"] is False
assert A["accounting"]["incremental_spend_usd"]==0 and A["accounting"]["terminal_cases_consumed"]==0
assert A["accounting"]["acceptance_credit_delta"]==0

ts=T["sources"]["root2_closure_v2_current_frontier"]
assert ts["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert ts["git_blob_sha"]==FILES["frontier"][1]
assert ts["verification_git_blob_sha"]==FILES["projection"][1]
assert ts["activation_git_blob_sha"]==FILES["activation"][1]
assert ts["effective_scheduling_authority"] is True
assert T["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert T["truth"]["achieved"] is False
assert "ROOT2_V6_ACTIVE_ZERO_REALITY_FRONTIER" in T["next_terminal_action"]

rc=R["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert rc["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert rc["current_frontier_git_blob_sha"]==FILES["frontier"][1]
assert rc["current_frontier_verification_git_blob_sha"]==FILES["projection"][1]
assert rc["current_frontier_activation_git_blob_sha"]==FILES["activation"][1]
assert rc["effective_scheduling_authority"] is True and rc["fresh_reality_authority"] is False
assert R["current_acceptance"]["accepted_families"]==5
assert R["current_acceptance"]["open_families"]==14
assert R["current_acceptance"]["proved_atomic"]==12
assert R["current_acceptance"]["unresolved_atomic"]==26
assert R["current_acceptance"]["terminal"] is False
assert R["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert R["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert R["root3_current_execution_state"]["path"]=="canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json"
assert R["root3_current_execution_state"]["fresh_reality_authority"] is False

bc=B["root2_closure_controller_v2"]
assert bc["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"
assert bc["frontier_git_blob_sha"]==FILES["frontier"][1]
assert bc["frontier_verification_git_blob_sha"]==FILES["projection"][1]
assert bc["frontier_activation_git_blob_sha"]==FILES["activation"][1]
assert bc["effective_scheduling_authority"] is True
assert B["incremental_spend_usd"]==0 and B["terminal_cases_consumed"]==0
assert B["execution_authority"] is False and B["promotion_authority"] is False and B["fresh_reality_authority"] is False
assert "ROOT2_V6_ZERO_REALITY_FRONTIER" in B["next"]

print("PASS__EXACT_ROOT2_V6_POINTER_BYTES__THREE_SURFACES_COHERENT__COUNTS_STABLE__ROOT3_PRESERVED__SCHEDULING_ONLY__NO_FRESH_REALITY__ZERO_CREDIT")
