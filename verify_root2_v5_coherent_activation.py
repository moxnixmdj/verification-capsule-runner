import json,pathlib,subprocess
P={"t":"subject/CURRENT_TERMINAL_AUTHORITY_V1.json","m":"subject/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json","r":"subject/TERMINAL_ROOT_CAUSE_STATE_V1.json","a":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5_ACTIVATION_V1.json"}
H={"t":"09073acc898ebb2f6091f4afe396c4e0ddcabb16","m":"3e7786a5618f4c6c31a1b072af1d25ef34c56874","r":"45faf1ff23c9f888c617bb1f4e83dba785af494b","a":"2d15df0daab51c5cc61c4194197da7f7fcd5a1b0"}
for k,p in P.items(): assert subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()==H[k]
t,m,r,a=[json.loads(pathlib.Path(P[k]).read_text()) for k in "tmra"]
F="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"; FS="e948022f0a4e8d91b949a5155d850d56aa137c87"
A="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5_ACTIVATION_V1.json"; AS=H["a"]
V="canonical/verification/ROOT2_V5_PROJECTION_VERIFICATION_20261004_V1.json"; VS="2475a8583e2ed2889c3e9e0613ae3bcf269ffc82"
x=t["sources"]["root2_closure_v2_current_frontier"]; assert (x["path"],x["git_blob_sha"],x["activation"],x["activation_git_blob_sha"],x["verification"],x["verification_git_blob_sha"])==(F,FS,A,AS,V,VS); assert x["effective_scheduling_authority"]
y=m["root2_closure_controller_v2"]; assert (y["frontier_path"],y["frontier_git_blob_sha"],y["frontier_activation_path"],y["frontier_activation_git_blob_sha"],y["frontier_verification_path"],y["frontier_verification_git_blob_sha"])==(F,FS,A,AS,V,VS); assert y["effective_scheduling_authority"]
z=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]; assert (z["current_frontier_path"],z["current_frontier_git_blob_sha"],z["current_frontier_activation_path"],z["current_frontier_activation_git_blob_sha"],z["current_frontier_verification_path"],z["current_frontier_verification_git_blob_sha"])==(F,FS,A,AS,V,VS)
assert r["current_acceptance"]["accepted_families"]==5 and r["current_acceptance"]["proved_atomic"]==12 and r["current_acceptance"]["unresolved_atomic"]==26 and not r["current_acceptance"]["terminal"]
assert r["root3_current_execution_state"]["currently_runnable_event_count"]==0 and not r["root3_current_execution_state"]["fresh_reality_authority"]
assert a["subject"]["git_blob_sha"]==FS and a["verification"]["git_blob_sha"]==VS and a["authority"]["effective_scheduling_authority"] and not a["authority"]["fresh_reality_authority"]
assert not m["execution_authority"] and not m["promotion_authority"] and not m["fresh_reality_authority"] and m["incremental_spend_usd"]==0 and m["terminal_cases_consumed"]==0
print("ROOT2_V5_COHERENT_ACTIVATION_PASS")
