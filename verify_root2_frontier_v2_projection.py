import hashlib, json, pathlib

BASE=pathlib.Path("subject/root2_frontier_v2_projection")
EXPECTED={
 "frontier":"36013ab1768260cca9dca4dbe1aa11a68dab56cf",
 "buildkite":"2725cf6820fb7ce6025213d474b9acf2937282ee",
 "subject_verification":"26ae22c52556c0505105dd5c3f1aa38544ec6387",
 "activation":"a9fa1e00d37c7977c4639b9369fb4eab2831e07d",
 "terminal":"a8b929995531f3165bc2c591a2d4b1330fd1b504",
 "root":"fd4b0e54f1e81fc6a478e7c4622df5dde368112c",
 "bridge":"f5528f296aec0baf138971d4d0d50565acf0db60",
}
FILES={
 "frontier":BASE/"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json",
 "buildkite":BASE/"TB4_BUILDKITE_ALL_ACCESS_TRIAL_CARRIER_CANDIDATE_20261004_V1.json",
 "subject_verification":BASE/"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "activation":BASE/"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2_ACTIVATION_V1.json",
 "terminal":BASE/"CURRENT_TERMINAL_AUTHORITY_V1.json",
 "root":BASE/"TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "bridge":BASE/"ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json",
}
def blob_sha(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in FILES.items():
 got=blob_sha(p)
 assert got==EXPECTED[k], (k,got,EXPECTED[k])
def load(k): return json.loads(FILES[k].read_text())

fr=load("frontier"); bk=load("buildkite"); ver=load("subject_verification")
act=load("activation"); term=load("terminal"); root=load("root"); bridge=load("bridge")

assert ver["independent_runner"]["pull_request"]==1547
assert ver["independent_runner"]["workflow_run_id"]==37166431994
assert ver["independent_runner"]["workflow_job_id"]==111330169951
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["subject"]["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert ver["subject"]["buildkite_candidate_git_blob_sha"]==EXPECTED["buildkite"]

delta=next(x for x in fr["verified_or_primary_source_deltas"] if x["target"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR")
assert delta["delete"]=="required_claim_coverage_noninferiority"
assert delta["remaining"]==["metric:matched_quality","matched_quality_noninferiority"]
assert fr["fresh_reality_authority"] is False
assert fr["accounting"]["acceptance_credit_delta"]==0
assert "TB4_BUILDKITE_ACCOUNT_AND_ZERO_CASE_PREFLIGHT_WHEN_TRIAL_ACCOUNT_ACCESS_IS_AVAILABLE" in fr["runnable_zero_reality"]

assert bk["narrow_conclusion"]["tb4_carrier_admissibility_proved"] is False
assert bk["terminal_cases_consumed"]==0
assert bk["incremental_spend_usd"]==0

assert act["subject"]["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert act["verification"]["git_blob_sha"]==EXPECTED["subject_verification"]
assert act["authority"]["effective_scheduling_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False

ta=term["sources"]["root2_closure_v2_current_frontier"]
assert ta["path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json"
assert ta["git_blob_sha"]==EXPECTED["frontier"]
assert ta["activation_git_blob_sha"]==EXPECTED["activation"]
assert ta["verification_git_blob_sha"]==EXPECTED["subject_verification"]
assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False
assert any("SYNTHESIS_SCOPE_AND_REQUIRED_CLAIM_COVERAGE_INDEPENDENT_PASS" in x for x in term["residual"])
assert term["sources"]["tb4_buildkite_material_wake"]["status"].startswith("NAMED_MATERIAL_WAKE_ONLY")

ra=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ra["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json"
assert ra["current_frontier_git_blob_sha"]==EXPECTED["frontier"]
assert ra["current_frontier_activation_git_blob_sha"]==EXPECTED["activation"]
assert root["current_acceptance"]=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
assert root["synthesis_scope_reclassification"]["remaining_root2_residuals"]==["metric:matched_quality","matched_quality_noninferiority"]

br=bridge["root2_closure_controller_v2"]
assert br["frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json"
assert br["frontier_git_blob_sha"]==EXPECTED["frontier"]
assert br["frontier_activation_git_blob_sha"]==EXPECTED["activation"]

print("ROOT2_FRONTIER_V2_POINTER_PROJECTION_PUBLIC_RUNNER_PASS")
