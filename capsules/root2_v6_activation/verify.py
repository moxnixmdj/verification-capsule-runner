import json,pathlib,subprocess
D="capsules/root2_v6_activation/"
P={"v":D+"verification.json","a":D+"activation.json","r":D+"root.json","m":D+"bridge.json","t":D+"terminal.json"}
H={"v":"b3f4035c6565261eacc22c4b745d233fdf091efa","a":"ce773f87ca56b570cd1ce42b9dde5554f916f6e0","r":"a040f96ddaa1df0a95e2ceceab40cb3e422487ad","m":"978ced5aa35d7ecdd5ec4076d090c291ddc2a391","t":"cf4f9b8ad64920ee0cfb4f80fec8a01699240aba"}
for k,p in P.items(): assert subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()==H[k]
v,a,r,m,t=[json.loads(pathlib.Path(P[k]).read_text()) for k in "varmt"]
F="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"; FS="fcbdb818b63b4986b026db29c400a47373a26fdb"
A="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6_ACTIVATION_V1.json"; AS=H["a"]
V="canonical/verification/ROOT2_V6_FINANCE_COMPRESSION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"; VS=H["v"]
assert v["subject"]["git_blob_sha"]==FS and v["independent_runner"]["conclusion"]=="success"
assert (v["verified"]["accepted_families"],v["verified"]["proved_atomic"],v["verified"]["unresolved_atomic"])==(5,12,26)
assert a["subject"]["git_blob_sha"]==FS and a["verification"]["git_blob_sha"]==VS
assert a["authority"]["effective_scheduling_authority"] and not a["authority"]["execution_authority"] and not a["authority"]["promotion_authority"] and not a["authority"]["fresh_reality_authority"]
z=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert (z["current_frontier_path"],z["current_frontier_git_blob_sha"],z["current_frontier_activation_path"],z["current_frontier_activation_git_blob_sha"],z["current_frontier_verification_path"],z["current_frontier_verification_git_blob_sha"])==(F,FS,A,AS,V,VS)
assert z["effective_scheduling_authority"] and r["scheduler_policy"]["root2_current_frontier"]==F and r["scheduler_policy"]["root2_effective_scheduling_authority"]
assert (r["current_acceptance"]["accepted_families"],r["current_acceptance"]["proved_atomic"],r["current_acceptance"]["unresolved_atomic"],r["current_acceptance"]["terminal"])==(5,12,26,False)
y=m["root2_closure_controller_v2"]
assert (y["frontier_path"],y["frontier_git_blob_sha"],y["frontier_activation_path"],y["frontier_activation_git_blob_sha"],y["frontier_verification_path"],y["frontier_verification_git_blob_sha"])==(F,FS,A,AS,V,VS)
assert y["effective_scheduling_authority"] and not m["execution_authority"] and not m["promotion_authority"] and not m["fresh_reality_authority"]
x=t["sources"]["root2_closure_v2_current_frontier"]
assert (x["path"],x["git_blob_sha"],x["activation"],x["activation_git_blob_sha"],x["verification"],x["verification_git_blob_sha"])==(F,FS,A,AS,V,VS)
assert x["effective_scheduling_authority"] and t["sources"]["terminal_root_cause_state_v1"]["git_blob_sha"]==H["r"]
assert t["truth"]["opus55_acceptance"].startswith("5/19") and t["truth"]["achieved"] is False
assert t["next_terminal_action"].startswith("ROOT2_V6_ACTIVE_ZERO_REALITY_FRONTIER")
print("PASS__ROOT2_V6_ACTIVATION__EXACT_FIVE_BLOBS__POINTER_COHERENCE__COUNTS_STABLE__ZERO_FRESH_REALITY")
