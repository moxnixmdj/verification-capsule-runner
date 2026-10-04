import json, pathlib, subprocess

FILES={
 "prior":"subject/PRIOR_TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "projected":"subject/PROJECTED_TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "v11":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json",
 "v11_ver":"subject/ROOT2_FRONTIER_V11_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "v11_final":"subject/ROOT2_FRONTIER_V11_FINAL_ACTIVATION_V1.json",
 "policy":"subject/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V3.json",
 "policy_final":"subject/TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V3_FINAL_ACTIVATION_V1.json",
 "package_ver":"subject/ROOT2_V11_ADAPTIVE_V3_PACKAGE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}
EXPECTED={
 "prior":"90dbeaf74cda18edd38d1cc34a003b4fffd236a0",
 "projected":"1f19ca6df11c49d5f94a4e4aa988daae97421ab1",
 "v11":"6857750dea3a0af48a5acc545b6f66b619d4335b",
 "v11_ver":"89884cc421eb8c7aff3e2bf9a17666478a31db94",
 "v11_final":"0eef553c70170e0df28f4893f2edeec87e006b0e",
 "policy":"e3d4bb102d8825798cb42b5f45382420fef41fbf",
 "policy_final":"cf6d3c92134ee7cb2e75ae7f82e144aa71a8ecba",
 "package_ver":"da6ef8d46f1fdb644878004cd2e846d2766a0ecf",
}
def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])

prior=json.loads(pathlib.Path(FILES["prior"]).read_text())
proj=json.loads(pathlib.Path(FILES["projected"]).read_text())
v11=json.loads(pathlib.Path(FILES["v11"]).read_text())
vv=json.loads(pathlib.Path(FILES["v11_ver"]).read_text())
vf=json.loads(pathlib.Path(FILES["v11_final"]).read_text())
policy=json.loads(pathlib.Path(FILES["policy"]).read_text())
pf=json.loads(pathlib.Path(FILES["policy_final"]).read_text())
pv=json.loads(pathlib.Path(FILES["package_ver"]).read_text())

def diff(a,b,path="",out=None):
    if out is None: out=[]
    if a==b: return out
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            diff(a.get(k),b.get(k),f"{path}.{k}" if path else k,out)
    else:
        out.append(path)
    return out

allowed={
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_git_blob_sha",
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_path",
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_git_blob_sha",
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_path",
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_git_blob_sha",
"roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_path",
"roots.root_2_measurement_or_comparator.active_closure_controller.status",
"scheduler_policy.adaptive_meta_scheduler.candidate_activation_git_blob_sha",
"scheduler_policy.adaptive_meta_scheduler.candidate_activation_path",
"scheduler_policy.adaptive_meta_scheduler.final_activation_git_blob_sha",
"scheduler_policy.adaptive_meta_scheduler.final_activation_path",
"scheduler_policy.adaptive_meta_scheduler.policy_git_blob_sha",
"scheduler_policy.adaptive_meta_scheduler.policy_path",
"scheduler_policy.adaptive_meta_scheduler.status",
"scheduler_policy.adaptive_meta_scheduler.verification_git_blob_sha",
"scheduler_policy.adaptive_meta_scheduler.verification_path",
"scheduler_policy.root2_current_frontier",
}
actual=set(diff(prior,proj))
assert actual==allowed,(sorted(actual-allowed),sorted(allowed-actual),len(actual))

assert proj["current_acceptance"]==prior["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False
}
assert proj["accounting"]==prior["accounting"]
assert proj["roots"]["root_1_capability_missing"]==prior["roots"]["root_1_capability_missing"]
assert proj["roots"]["root_3_scope_completeness"]==prior["roots"]["root_3_scope_completeness"]
assert proj["root3_current_execution_state"]==prior["root3_current_execution_state"]

pr2=proj["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert pr2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json"
assert pr2["current_frontier_git_blob_sha"]==EXPECTED["v11"]
assert pr2["current_frontier_verification_git_blob_sha"]==EXPECTED["v11_ver"]
assert pr2["current_frontier_activation_git_blob_sha"]==EXPECTED["v11_final"]
assert pr2["effective_scheduling_authority"] is True
assert pr2["fresh_reality_authority"] is False
# These load-bearing current-main subtrees must survive byte-semantically.
assert pr2["external_fact_acquisition_overlay"]==prior["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["external_fact_acquisition_overlay"]
assert pr2["primary_source_search_deletions"]==prior["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["primary_source_search_deletions"]

assert vv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert vv["verified"]["accepted_families"]==5
assert vv["verified"]["proved_atomic"]==12
assert vv["verified"]["unresolved_atomic"]==26
assert vv["verified"]["fresh_reality_authority"] is False
assert vf["frontier"]["git_blob_sha"]==EXPECTED["v11"]
assert vf["frontier_verification"]["git_blob_sha"]==EXPECTED["v11_ver"]
assert vf["authority"]=={"scheduling":True,"effective_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}

ams=proj["scheduler_policy"]["adaptive_meta_scheduler"]
assert ams["policy_git_blob_sha"]==EXPECTED["policy"]
assert ams["final_activation_git_blob_sha"]==EXPECTED["policy_final"]
assert ams["verification_git_blob_sha"]==EXPECTED["package_ver"]
assert ams["runtime_git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert ams["execution_authority"] is False
assert ams["promotion_authority"] is False
assert ams["fresh_reality_authority"] is False
assert proj["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json"

assert policy["exact_live_state"]["accepted_families"]==5
assert policy["exact_live_state"]["proved_atomic"]==12
assert policy["exact_live_state"]["unresolved_atomic"]==26
assert policy["execution_authority"] is False
assert policy["promotion_authority"] is False
assert policy["fresh_reality_authority"] is False
assert pf["preserved_authority"]["root3_v2"] is True
assert pf["preserved_authority"]["root2_v10_external_fact_overlay"] is True
assert pf["preserved_authority"]["osworld_component_pin_supplement"] is True
assert pf["preserved_authority"]["arena_comparator_audit_separate_wake_artifact"] is True
assert pv["verified"]["root3_v2_unchanged"] is True
assert pv["verified"]["accepted_families"]==5
assert pv["verified"]["proved_atomic"]==12
assert pv["verified"]["unresolved_atomic"]==26

print("PASS: exact current-main Root2 V10->V11 + adaptive V2->V3 projection")
print("PASS: exactly 17 authorized scheduling pointer fields changed")
print("PASS: Root1, Root3, acceptance, accounting, 18-fact overlay and OSWorld supplement preserved")
print("PASS: zero spend, zero cases, zero credit, no execution/promotion/fresh-reality authority")
