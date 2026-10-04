import json, pathlib, subprocess

A="subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4_ACTIVATION_V1.json"
V="subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

assert blob(A)=="53a34935ae664e89f53caf486366f7f3484ed0f4"
assert blob(V)=="d3e116d3613b0666648733491449f13a8127a543"

a=json.loads(pathlib.Path(A).read_text())
v=json.loads(pathlib.Path(V).read_text())

assert a["subject"]["frontier_git_blob_sha"]=="8c90a1dc4903f9b895788ff2864822d6ebc26ac9"
assert a["verification"]["git_blob_sha"]=="d3e116d3613b0666648733491449f13a8127a543"
assert a["verification"]["workflow_run_id"]==37167894272
assert a["verification"]["workflow_job_id"]==111334602272
assert a["verification"]["conclusion"]=="success"
assert a["authority"]["effective_scheduling_authority"] is False
assert a["authority"]["execution_authority"] is False
assert a["authority"]["promotion_authority"] is False
assert a["authority"]["fresh_reality_authority"] is False
assert a["accounting"]["incremental_spend_usd"]==0
assert a["accounting"]["terminal_cases_consumed"]==0
assert a["accounting"]["acceptance_credit_delta"]==0

assert v["subject"]["frontier_git_blob_sha"]=="8c90a1dc4903f9b895788ff2864822d6ebc26ac9"
assert v["independent_runner"]["verifier_merge_commit"]=="50b14ebedc5cfb5933e5b1fd08680e792f028bed"
assert v["independent_runner"]["workflow_run_id"]==37167894272
assert v["independent_runner"]["workflow_job_id"]==111334602272
assert v["verified"]["root2_touching_predicates"]==19
assert v["verified"]["circleci_account_runtime_residual_count"]==8
assert v["verified"]["fresh_reality_authority"] is False
assert v["accounting"]["incremental_spend_usd"]==0
assert v["accounting"]["terminal_cases_consumed"]==0
assert v["accounting"]["acceptance_credit_delta"]==0

print("ROOT2_V4_ACTIVATION_CANDIDATE_PASS")
