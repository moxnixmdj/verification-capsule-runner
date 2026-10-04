import json, pathlib, subprocess

A="subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_ACTIVATION_V1.json"
V="subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

def b(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()

assert b(A)=="76d36bc34947e726502d0c8fc1dbb961d6442c88"
assert b(V)=="8436a9eb30312b959ba094394e60f26b4833a3a2"
a=json.loads(pathlib.Path(A).read_text())
v=json.loads(pathlib.Path(V).read_text())
assert a["subject"]["frontier_git_blob_sha"]=="681123ef6cff3506d66af6b31b61c8bc14a8a913"
assert a["verification"]["workflow_run_id"]==37167173550
assert a["verification"]["conclusion"]=="success"
assert a["authority"]["effective_scheduling_authority"] is False
assert a["authority"]["execution_authority"] is False
assert a["authority"]["fresh_reality_authority"] is False
assert v["independent_runner"]["verifier_merge_commit"]=="34da56b694b59ab25cc3f93977b54746d87df5f5"
assert v["verified"]["tb4_carrier_admissibility_proved"] is False
assert v["verified"]["fresh_reality_authority"] is False
assert v["terminal_cases_consumed"]==0
assert v["incremental_spend_usd"]==0
print("ROOT2_V3_ACTIVATION_CANDIDATE_PASS")
